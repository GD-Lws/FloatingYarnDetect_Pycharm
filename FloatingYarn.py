import ctypes
import math
import time
from collections import deque
from enum import Enum

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QThread, QMutex, QTimer, QWaitCondition, QMutexLocker
from PyQt5.QtWidgets import QApplication, QWidget, QListWidget, QVBoxLayout, QTextEdit, QPushButton, QMainWindow, \
    QMessageBox

from CAN_TOOL.CANMessageData import CANMessageData
from CAN_TOOL.Can_Derive import Can_Derive
import sys
from datetime import datetime
from FYCanThread import FYCanThread


def cameraParams2CtypeArray(value_str, length=5):
    # 创建 ctypes 数组
    ctype_array = (ctypes.c_uint8 * length)()
    # 计算填充字节
    padding = length - len(value_str)
    # 填充前面的 0x00
    for i in range(padding):
        ctype_array[i] = 0x30
    # 填充实际的 ASCII 字符
    for i, char in enumerate(value_str):
        if i + padding < length:
            ctype_array[i + padding] = ord(char)
    return ctype_array


def calNumberArray(input_list):
    if len(input_list) != 8:
        return -1
    outputData = 0
    for i in range(8):
        data = input_list[i] - 48
        multiData = 10 ** (7 - i)
        outputData = outputData + data * multiData
    return outputData


def list_to_str(input_list):
    """将十进制 ASCII 列表转换为字符串，并附加接收时间戳"""
    message_str = ''
    if isinstance(input_list, list):
        try:
            # 将每个十进制数转换为 ASCII 字符
            message_str = ''.join(chr(value) for value in input_list)
        except ValueError:
            message_str = 'Invalid ASCII values'

    # 获取当前时间戳
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 将时间戳添加到字符串末尾
    message_str += f' (Received at: {timestamp})'

    return message_str


def show_error_dialog(parent, msg):
    """显示错误对话框"""
    QMessageBox.critical(parent, 'Error', msg, QMessageBox.Ok)


# input_arr 是接收的数据
def compare_arr_ctypes_(input_arr, target_arr):
    arrTarget_int = [int(x) for x in target_arr]
    for i in range(8):
        if input_arr[i] != arrTarget_int[i]:
            return False
    return True


def on_timeout():
    """超时处理，弹出错误对话框"""
    print("Timeout occurred. No response received.")
    showErrorDialog(None, 'Timeout occurred. No response received.')  # None 为父窗口


class FloatingYarn(Can_Derive, QObject):
    sig_messageReceived = pyqtSignal(str)
    sig_statusUpdated = pyqtSignal(str, str)
    sig_imageProcess = pyqtSignal()
    sig_progressValue = pyqtSignal(int)
    sig_canStatus = pyqtSignal(bool)

    class MachineStatus(Enum):
        Close = 0
        Open = 1
        Ready = 2
        Activity = 3
        Edit = 4
        PIC = 5

    class MachineOperate(Enum):
        Detect = 0
        Compare = 1
        Record = 2

    def __init__(self, win_linux=1, Can_id=0x141, max_messages=10000,
                 temp_photo_storage_path='rec_txt/output_image.jpg'):
        QObject.__init__(self)
        Can_Derive.__init__(self, win_linux=win_linux)

        self.StdData = CANMessageData()
        self.received_messages = deque(maxlen=max_messages)
        self.received_image_arr = deque()
        self.received_image_flag = False
        self.__selfStatus = self.MachineStatus.Close
        self.__selfOperateMode = self.MachineOperate.Detect
        self.__canID = Can_id
        self.__canBaudRate = 1000
        self.__canStatus = False

        self.__recMsgFinishIndex = 0
        self.__msgFinishArray = [8, 9, 10, 11, 12, 13, 14, 15]
        self.__msgStartArray = [0, 1, 2, 3, 4, 5, 6, 7]
        self.__imageSavePath = temp_photo_storage_path

        # 启动接收线程
        self.wait_condition = QWaitCondition()
        self.mutex = QMutex()

        # 启动接收线程
        self.receiver_thread = CanReceiverThread(wait_condition=self.wait_condition, mutex=self.mutex)
        self.receiver_thread.set_floating_yarn(self)
        self.receiver_thread.start()

        # 用于数据接收处理线程
        self.processor_thread = None
        # 用于持续发送当前编织行数
        self.__knit_row = 0
        self.sendKnit_thread = None

        self.__pic_all_len = 0
        self.__pic_rec_len = 0

    def start_processing_thread(self, thread_index):
        if thread_index == 0:
            if self.processor_thread is None:
                # 启动处理线程
                self.processor_thread = CanProcessorThread(wait_condition=self.wait_condition, mutex=self.mutex)
                self.processor_thread.set_floating_yarn(self)
                self.processor_thread.start()
            else:
                print("processing thread is running!")
        elif thread_index == 1:
            if self.sendKnit_thread is None:
                self.sendKnit_thread = KnitSendThread(wait_condition=self.wait_condition, mutex=self.mutex)
                self.sendKnit_thread.set_floating_yarn(self)
                self.sendKnit_thread.start()
            else:
                print("sendKnit_thread is running!")
        else:
            print("thread index error!")

    def stop_processing_thread(self, thread_index):
        if thread_index == 0:
            if self.processor_thread is not None:
                self.processor_thread.requestInterruption()  # 触发线程停止
                self.processor_thread.wait()  # 等待线程结束
                self.processor_thread = None
            else:
                print("processing thread is running!")
        elif thread_index == 1:
            if self.sendKnit_thread is not None:
                self.sendKnit_thread.requestInterruption()  # 触发线程停止
                self.sendKnit_thread.wait()  # 等待线程结束
                self.sendKnit_thread = None
            else:
                print("sendKnit_thread is running!")
        else:
            print("thread index error!")

    # 检查结束符号
    def detectSpecificCharacters(self, data_list, target_list):
        msg_finish_set = set(target_list)
        target_len = len(target_list)
        finish_count = 0  # 当前匹配的序列长度

        for data in data_list:
            if data in msg_finish_set:
                # 只有当数据匹配目标序列的当前索引时才进行处理
                if data == target_list[finish_count]:
                    finish_count += 1
                    # 如果完成了整个序列的匹配
                    if finish_count == target_len:
                        self.__recMsgFinishIndex = 0
                        if self.received_image_flag:
                            self.received_image_flag = False
                            self.stop_processing_thread(0)
                            self.dequeToImage()  # 转换数据为图片
                            self.fyCanSendData(self.StdData.arrEND)
                            print("图片接收完成")
                        # 终止当前检查，避免继续不必要的检查
                        return True
                else:
                    # 匹配失败，重置计数
                    finish_count = 0
            else:
                # 数据不在目标序列中，重置计数
                finish_count = 0
        return False

    def dequeToImage(self):
        print(len(self.received_image_arr))
        image_array = bytearray()  # 使用 bytearray 存储数据
        hex_str = ''
        # 处理起始标识符
        while True:
            if not self.received_image_arr:
                print("没有找到起始标识符数组")
                return False

            data_list = self.received_image_arr.popleft()

            # 调用 detectSpecificCharacters 并检查是否找到 target_list
            if self.detectSpecificCharacters(data_list, target_list=[0, 1, 2, 3, 4, 5, 6, 7]):
                print("找到起始标识符数组")
                break  # 如果找到 target_list，退出循环
        end_array = self.received_image_arr[-1]
        end_array = self.received_image_arr.pop()
        # 处理图像数据
        while self.received_image_arr:
            data_list = self.received_image_arr.popleft()  # 从左边弹出
            # 将 data_list 中的每个字节直接追加到 image_array
            image_array.extend(data_list)  # 将字节追加到 bytearray

        output_image_path = self.__imageSavePath
        with open(output_image_path, 'wb') as image_file:
            image_file.write(image_array)

        print(f'图像已保存到 {output_image_path}')
        self.sig_imageProcess.emit()

    def fyStopImageRec(self):
        self.fyCanSendData(self.StdData.arrEND)
        self.received_image_flag = False
        self.stop_processing_thread(0)

    # 接收数据处理
    def receiving_msg_processing(self, vci_can_obj):
        data_list = list(vci_can_obj.Data)
        with QMutexLocker(self.mutex):  # 确保线程安全
            if self.received_image_flag:
                # print(data_list)  # 直接输出接收到的数据
                self.received_image_arr.append(data_list)
                self.__pic_rec_len += 8
                self.calPicProgressBar()
                if not self.processor_thread:
                    self.start_processing_thread(0)  # 开始处理线程
            else:
                self.received_messages.append(data_list)
                self.wait_condition.wakeAll()  # 唤醒等待的线程
                # 发射信号，确保在主线程中
                self.sig_messageReceived.emit(list_to_str(data_list))

    def calPicProgressBar(self):
        if self.__pic_all_len != 0 and self.__pic_rec_len != 0:
            # 计算百分比（浮点数）
            percentage = (self.__pic_rec_len / self.__pic_all_len) * 100
            self.sig_progressValue.emit(percentage)

    # CAN关启动
    def fyCanOpen(self, canBaud=1000):
        self.can_init()
        self.can_channel_open(baud=canBaud)
        if self.check_CAN_STATUS():
            self.__canStatus = True
            self.sig_canStatus.emit(self.__canStatus)
            return True
        else:
            self.__canStatus = False
            self.sig_canStatus.emit(self.__canStatus)
            return False

    # CAN关闭
    def fyCanClose(self):
        self.can_close()
        self.__canStatus = False
        self.sig_canStatus.emit(self.__canStatus)

    # 下位机运行状态检查
    def checkSlaveStatus(self):
        rec_msg, rec_flag = self.fySendDataAndWait(message=self.StdData.arrSTATUS, timeout_ms=1000)
        if rec_flag:
            if rec_msg[2] == 49:
                self.__selfStatus = self.MachineStatus.Open
            elif rec_msg[2] == 50:
                self.__selfStatus = self.MachineStatus.Ready
            elif rec_msg[2] == 51:
                self.__selfStatus = self.MachineStatus.Activity
            elif rec_msg[2] == 52:
                self.__selfStatus = self.MachineStatus.Edit
            elif rec_msg[2] == 53:
                self.__selfStatus = self.MachineStatus.PIC
            elif rec_msg[2] == 54:
                self.__selfStatus = self.MachineStatus.PIC
            if rec_msg[5] == 49:
                self.__selfOperateMode = self.MachineOperate.Detect
            elif rec_msg[5] == 50:
                self.__selfOperateMode = self.MachineOperate.Compare
            elif rec_msg == 51:
                self.__selfOperateMode = self.MachineOperate.Record
            print('当前下位机运行状态')
            print(self.__selfStatus)
            self.sig_statusUpdated.emit(str(self.__selfStatus), str(self.__selfOperateMode))
            return True
        else:
            print("Failed to receive message.")
            return False

    def fyCanSendData(self, send_data):
        self.change_send_data(send_data)
        self.can_send_msg()

    def fyDelaySendData(self, msg, delay_time=100):
        QTimer.singleShot(delay_time, lambda: self.fyCanSendData(msg))

        # 发送数据并等待接收

    def fySendDataAndWait(self, message, timeout_ms=5000):
        """发送数据并等待接收，带超时机制"""
        self.fyCanSendData(message)
        # 设置超时机制
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(on_timeout)
        timer.start(timeout_ms)

        data_received = False

        with QMutexLocker(self.mutex):
            # 使用 QWaitCondition 和 QMutex 进行同步
            data_received = self.wait_condition.wait(self.mutex, timeout_ms)

        # 停止定时器
        timer.stop()

        if not data_received:
            # 处理超时情况
            on_timeout()
            return None, False  # 返回 None 表示未接收到数据，False 表示操作失败

        # 返回接收到的数据和成功标志
        if self.received_messages:
            data_rec = self.received_messages[-1]
            # err_flag = True
            # err_arr = [0x45, 0x72, 0x72]
            # for i in range(3):
            #     if data_rec[i] != err_arr[i]:
            #         err_flag = False
            # if err_flag:
            return data_rec, True
        else:
            return None, False

    def fySetCameraParameter(self, parameter_array, parameter_index):
        num_array = [0x00, 0x31, 0x32, 0x33, 0x34]
        # print(f'Value parameter_array: {[hex(x) for x in parameter_array]}')
        if self.checkSlaveStatus():
            if self.__selfStatus == self.MachineStatus.Ready:
                rec_msg, rec_flag = self.fySendDataAndWait(message=self.StdData.arrRE2ED)
                if rec_flag:
                    self.fySetCameraParameter(parameter_array, parameter_index)
                return True
            elif self.__selfStatus == self.MachineStatus.Edit:
                if parameter_index < 4:
                    sendMsg = self.StdData.arrS2ROI1
                elif 4 <= parameter_index <= 8:
                    sendMsg = self.StdData.arrS2CAM1
                else:
                    sendMsg = None  # 处理不符合条件的情况，避免未定义行为
                # 发送消息或进一步处理 sendMsg
                if sendMsg is not None:
                    if parameter_index == 1 or parameter_index == 4:
                        self.fyCanSendData(sendMsg)
                    time.sleep(0.05)
                    self.fySendDelayAndWaitACK(msg=parameter_array)
                else:
                    return False
            else:
                showErrorDialog(None, 'Machine Status Error.')
        else:
            return False

    def fySecondMessage(self, msg):
        # 延迟调用 fySendDelayAndWaitACK 方法
        QTimer.singleShot(1, lambda: self.fySendDelayAndWaitACK(msg))

    def fySendDelayAndWaitACK(self, msg):
        # 发送数据并等待ACK
        set_msg, set_flag = self.fySendDataAndWait(message=msg)
        # 处理返回结果
        print(f"Response: {set_msg}, Flag: {set_flag}")

    # 开始检测
    def fyStartDetect(self):
        if self.checkSlaveStatus():
            if self.__selfStatus == self.MachineStatus.Ready:
                rec_msg, rec_flag = self.fySendDataAndWait(message=self.StdData.arrRE2AC)
                if compare_arr_ctypes_(input_arr=rec_msg, target_arr=self.StdData.arrPCO):
                    print('AC:下位机处于PCO')
                    self.fyDelaySendData(self.StdData.arrACK, delay_time=10)
                    if self.checkSlaveStatus():
                        if self.__selfStatus == self.MachineStatus.Activity:
                            print('下位机状态已经是Activity')
                            self.fyDelaySendData(self.StdData.arrDetect, delay_time=1000)
                            self.start_processing_thread(1)
                            return True
                        else:
                            return False
                    else:
                        return False
                elif compare_arr_ctypes_(input_arr=rec_msg, target_arr=self.StdData.arrPCC):
                    print('AC:下位机处于PCC')
                    self.fyStartDetect()
                    return True
            elif self.__selfStatus == self.MachineStatus.Activity:

                self.fyCanSendData(self.StdData.arrSTA)
                return True
        else:
            return False

    # 检测停止
    def fyStopDetect(self):
        self.stop_processing_thread(1)
        self.fyDelaySendData(self.StdData.arrBA2RE, delay_time=1000)

    def fyReceiveImage(self):
        if self.checkSlaveStatus():
            if self.__selfStatus == self.MachineStatus.Ready:
                rec_msg, rec_flag = self.fySendDataAndWait(message=self.StdData.arrRE2PC)
                if compare_arr_ctypes_(input_arr=rec_msg, target_arr=self.StdData.arrPCO):
                    print('PIC:下位机处于PCO')
                    self.fyDelaySendData(self.StdData.arrACK, delay_time=10)
                    if self.checkSlaveStatus():
                        if self.__selfStatus == self.MachineStatus.PIC:
                            print('下位机状态已经是PIC')
                            self.received_image_arr.clear()
                            self.__recMsgFinishIndex = 0
                            len_msg, rec_flag = self.fySendDataAndWait(message=self.StdData.arrSTA)
                            self.__pic_all_len = calNumberArray(len_msg)
                            self.__pic_rec_len = 0
                            self.sig_progressValue.emit(0)
                            self.received_image_flag = True
                            return True
                        else:
                            return False
                    else:
                        return False
                elif compare_arr_ctypes_(input_arr=rec_msg, target_arr=self.StdData.arrPCC):
                    print('PIC:下位机处于PCC')
                    self.fyReceiveImage()
                    return True
            elif self.__selfStatus == self.MachineStatus.PIC:
                self.received_image_flag = True
                self.received_image_arr = []
                self.__recMsgFinishIndex = 0
                self.fyCanSendData(self.StdData.arrSTA)
                return True
            else:
                showErrorDialog(None, 'Machine Status Error.')
                return False
        else:
            return False

    # 状态转换
    def trans_status(self, target_status):
        if self.checkSlaveStatus():
            if self.__selfStatus == self.MachineStatus.Ready:
                if target_status == self.MachineStatus.Ready:
                    return 1
                elif target_status == self.MachineStatus.PIC:
                    self.change_send_data(self.StdData.arrRE2PC)
                elif target_status == self.MachineStatus.Edit:
                    self.change_send_data(self.StdData.arrRE2ED)
                elif target_status == self.MachineStatus.Activity:
                    self.change_send_data(self.StdData.arrRE2AC)
                else:
                    return -1
            elif self.__selfStatus == self.MachineStatus.Edit:
                if target_status == self.MachineStatus.Ready:
                    self.change_send_data(self.StdData.arrBA2RE)
                else:
                    return -1
            elif self.__selfStatus == self.MachineStatus.Activity:
                if target_status == self.MachineStatus.Ready:
                    self.change_send_data(self.StdData.arrBA2RE)
                else:
                    return -1
            elif self.__selfStatus == self.MachineStatus.PIC:
                if target_status == self.MachineStatus.Ready:
                    self.change_send_data(self.StdData.arrBA2RE)
                else:
                    return -1
            elif self.__selfStatus == self.MachineStatus.Open:
                if target_status == self.MachineStatus.Ready:
                    self.change_send_data(self.StdData.arrOP2RE)
                else:
                    return -1
            elif self.__selfStatus == self.MachineStatus.PIC:
                if target_status == self.MachineStatus.Ready:
                    self.change_send_data(self.StdData.arrEND)
                else:
                    return -1
            self.can_send_msg(send_id=self.__canID)
            return 1
        else:
            return -2

    def fyTrans2Ready(self):
        self.trans_status(self.MachineStatus.Ready)


class CanReceiverThread(FYCanThread):
    """线程用于接收数据"""

    def run(self):
        while not self.isInterruptionRequested():
            if self.floating_yarn:
                self.floating_yarn.can_receive_msg_2()
                with QMutexLocker(self.mutex):
                    if self.floating_yarn.received_messages:
                        self.wait_condition.wakeAll()  # 唤醒处理线程
            else:
                QThread.msleep(100)  # 延时，以避免占用过多 CPU 资源


class CanProcessorThread(FYCanThread):
    def run(self):
        if self.floating_yarn is not None:
            while not self.isInterruptionRequested():
                with QMutexLocker(self.mutex):
                    while not self.floating_yarn.received_image_arr and not self.isInterruptionRequested():
                        self.wait_condition.wait(self.mutex)  # 等待数据到达

                    if self.isInterruptionRequested():
                        break

                    if self.floating_yarn.received_image_arr:
                        data_list = self.floating_yarn.received_image_arr[-1]
                        if data_list:
                            self.floating_yarn.detectSpecificCharacters(
                                data_list=data_list,
                                target_list=[8, 9, 10, 11, 12, 13, 14, 15]
                            )


class KnitSendThread(FYCanThread):
    """线程用于发送数据"""

    def run(self):
        if self.floating_yarn is not None:
            send_data_array = self.floating_yarn.StdData.arrYARN
            sendRow = self.floating_yarn.__knit_row
            row_array = cameraParams2CtypeArray(value_str=sendRow, length=5)
            for i in range(3, 8):
                send_data_array[i] = row_array[i - 3]
            self.floating_yarn.fyCanSendData(send_data_array)


def showErrorDialog(parent, msg):
    QMessageBox.critical(parent, 'Error', msg, QMessageBox.Ok)


class FY_MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FloatingYarn Test")
        self.setGeometry(100, 100, 600, 400)
        self.floating_yarn = FloatingYarn()  # 实例化 FloatingYarn

        # 设置 UI
        self.init_ui()

    def init_ui(self):
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)

        self.list_widget = QListWidget(self)
        self.floating_yarn.sig_messageReceived.connect(self.display_message)
        self.send_button = QPushButton("Send Data and Wait", self)
        self.send_button.clicked.connect(self.on_send_button_click)

        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.send_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    @pyqtSlot()
    def on_send_button_click(self):
        self.text_edit.append("Sending data...")
        self.floating_yarn.fySendDataAndWait(self.floating_yarn.StdData.arrRE2PC)

    def display_message(self, msg):
        self.list_widget.addItem(msg)  # 将接收到的数据添加到列表


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FY_MainWindow()
    window.show()
    sys.exit(app.exec_())
