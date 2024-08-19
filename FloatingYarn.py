import ctypes
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
    sig_canStatus = pyqtSignal(bool,int)

    class MachineStatus(Enum):
        Close = 0
        Open = 1
        Ready = 2
        Activity = 3
        Edit = 4
        PIC = 5
        MSG_END = 6
        SQL_EDIT = 7

    class MachineOperate(Enum):
        Detect = 0
        Compare = 1
        Record = 2

    def __init__(self, win_linux=1, Can_id=0x141, max_messages=10000,
                 temp_photo_storage_path='rec_txt/output_image.jpg'):
        QObject.__init__(self)
        Can_Derive.__init__(self, win_linux=win_linux)

        self.StdData = CANMessageData()
        self._recMsgSaveArr = deque(maxlen=max_messages)
        self._recImageSaveArr = deque()
        self.__recImageFlag = False
        self.__selfStatus = self.MachineStatus.Close
        self.__selfOperateMode = self.MachineOperate.Detect
        self.__canID = Can_id
        self.__canBaudRate = 1000
        self.__canStatus = False

        self.__recMsgFinishIndex = 0
        self.__finishMsgArr = [8, 9, 10, 11, 12, 13, 14, 15]
        self.__startMsgArr = [0, 1, 2, 3, 4, 5, 6, 7]
        self.__imageSavePath = temp_photo_storage_path

        # 启动接收线程
        self.__waitCondition = QWaitCondition()
        self.__Mutex = QMutex()

        # 启动接收线程
        self.__recMsgThread = CanReceiverThread(wait_condition=self.__waitCondition, mutex=self.__Mutex)
        self.__recMsgThread.set_floating_yarn(self)
        self.__recMsgThread.start()

        # 用于数据接收处理线程
        self.__processorThread = None
        # 用于持续发送当前编织行数
        self.__knitRow = 0
        self.__sendKnitInfoThread = None

        self.__recPicAllSize = 0
        self.__recPicCurrentSize = 0

        self.__recSqlTabNameString = ""
        self.__recSqlTabNameArr = []
        self.__recSqlTabNameFlag = False

    def start_processing_thread(self, thread_index):
        if thread_index == 0:
            if self.__processorThread is None:
                # 启动处理线程
                self.__processorThread = CanProcessorThread(wait_condition=self.__waitCondition, mutex=self.__Mutex)
                self.__processorThread.set_floating_yarn(self)
                self.__processorThread.start()
            else:
                print("processing thread is running!")
        elif thread_index == 1:
            if self.__sendKnitInfoThread is None:
                self.__sendKnitInfoThread = KnitSendThread(wait_condition=self.__waitCondition, mutex=self.__Mutex)
                self.__sendKnitInfoThread.set_floating_yarn(self)
                self.__sendKnitInfoThread.start()
            else:
                print("sendKnit_thread is running!")
        else:
            print("thread index error!")

    def stop_processing_thread(self, thread_index):
        if thread_index == 0:
            if self.__processorThread is not None:
                self.__processorThread.requestInterruption()  # 触发线程停止
                self.__processorThread.wait()  # 等待线程结束
                self.__processorThread = None
            else:
                print("processing thread is running!")
        elif thread_index == 1:
            if self.__sendKnitInfoThread is not None:
                self.__sendKnitInfoThread.requestInterruption()  # 触发线程停止
                self.__sendKnitInfoThread.wait()  # 等待线程结束
                self.__sendKnitInfoThread = None
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
                        if self.__recImageFlag:
                            self.processDscImageFlag()
                        elif self.__recSqlTabNameFlag:
                            self.processDscSQLFlag()
                        return True
                else:
                    # 匹配失败，重置计数
                    finish_count = 0
            else:
                # 数据不在目标序列中，重置计数
                finish_count = 0
        return False

    def processDscImageFlag(self):
        self.__recImageFlag = False
        self.stop_processing_thread(0)
        self.dequeToImage()  # 转换数据为图片
        self.fyCanSendData(self.StdData.arrEND)
        self.sig_canStatus.emit(True, 0)
        print("图片接收完成")

    def processDscSQLFlag(self):
        pass

    def dequeToImage(self):
        print(len(self._recImageSaveArr))
        image_array = bytearray()  # 使用 bytearray 存储数据
        hex_str = ''
        # 处理起始标识符
        while True:
            if not self._recImageSaveArr:
                print("没有找到起始标识符数组")
                return False
            data_list = self._recImageSaveArr.popleft()
            # 调用 detectSpecificCharacters 并检查是否找到 target_list
            if self.detectSpecificCharacters(data_list, target_list=[0, 1, 2, 3, 4, 5, 6, 7]):
                print("找到起始标识符数组")
                break  # 如果找到 target_list，退出循环
        end_array = self._recImageSaveArr[-1]
        end_array = self._recImageSaveArr.pop()
        # 处理图像数据
        while self._recImageSaveArr:
            data_list = self._recImageSaveArr.popleft()  # 从左边弹出
            # 将 data_list 中的每个字节直接追加到 image_array
            image_array.extend(data_list)  # 将字节追加到 bytearray

        output_image_path = self.__imageSavePath
        with open(output_image_path, 'wb') as image_file:
            image_file.write(image_array)

        print(f'图像已保存到 {output_image_path}')
        self.sig_imageProcess.emit()

    def fyStopImageRec(self):
        self.fyCanSendData(self.StdData.arrEND)
        self.__recImageFlag = False
        self.stop_processing_thread(0)

    # 接收数据处理
    def receiving_msg_processing(self, vci_can_obj):
        data_list = list(vci_can_obj.Data)
        with QMutexLocker(self.__Mutex):  # 确保线程安全
            if self.__recImageFlag:
                self._recImageSaveArr.append(data_list)
                self.__recPicCurrentSize += 8
                self.fyCalPicProgressBar()
            elif self.__recSqlTabNameFlag:
                self.__recSqlTabNameArr.append(data_list)
            else:
                self._recMsgSaveArr.append(data_list)
                self.__waitCondition.wakeAll()  # 唤醒等待的线程
                self.sig_messageReceived.emit(list_to_str(data_list))  # 发射信号，确保在主线程中
            # 检查处理线程是否需要启动
            if (self.__recImageFlag or self.__recSqlTabNameFlag) and not self.__processorThread:
                self.start_processing_thread(0)  # 开始处理线程

    def fyCalPicProgressBar(self):
        if self.__recPicAllSize != 0 and self.__recPicCurrentSize != 0:
            # 计算百分比（浮点数）
            percentage = (self.__recPicCurrentSize / self.__recPicAllSize) * 100
            self.sig_progressValue.emit(percentage)

    # CAN关启动
    def fyCanOpen(self, canBaud=1000):
        self.can_init()
        self.can_channel_open(baud=canBaud)
        if self.check_CAN_STATUS():
            self.__canStatus = True
            self.sig_canStatus.emit(self.__canStatus, 0)
            return True
        else:
            self.__canStatus = False
            self.sig_canStatus.emit(self.__canStatus, 0)
            return False

    # CAN关闭
    def fyCanClose(self):
        self.can_close()
        self.__canStatus = False
        self.sig_canStatus.emit(self.__canStatus, 0)

    # 下位机运行状态检查
    def fyCheckSlaveStatus(self):
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
            if rec_msg[5] == 48:
                self.__selfOperateMode = self.MachineOperate.Detect
            elif rec_msg[5] == 49:
                self.__selfOperateMode = self.MachineOperate.Compare
            elif rec_msg[5] == 50:
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

    def fySendDelayData(self, msg, delay_time=100):
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

        with QMutexLocker(self.__Mutex):
            # 使用 QWaitCondition 和 QMutex 进行同步
            data_received = self.__waitCondition.wait(self.__Mutex, timeout_ms)

        # 停止定时器
        timer.stop()

        if not data_received:
            # 处理超时情况
            on_timeout()
            return None, False  # 返回 None 表示未接收到数据，False 表示操作失败

        # 返回接收到的数据和成功标志
        if self._recMsgSaveArr:
            data_rec = self._recMsgSaveArr[-1]
            # err_flag = True
            # err_arr = [0x45, 0x72, 0x72]
            # for i in range(3):
            #     if data_rec[i] != err_arr[i]:
            #         err_flag = False
            # if err_flag:
            return data_rec, True
        else:
            return None, False

    # def fySetSQLState(self, mission):
    #     if not self.checkSlaveStatus():
    #         return False
    #     # 处理设备状态为 Ready
    #     if self.__selfStatus == self.MachineStatus.Ready:
    #         rec_msg, rec_flag = self.fySendDataAndWait(message=self.StdData.arrRE2SQL)
    #         return self.fySetSQLState(mission)
    #     # 处理设备状态为 SQL
    #     if self.__selfStatus == self.MachineStatus.SQL_EDIT:
    #         # 获取文件名
    #         if mission == 1:
    #             self.fyCanSendData(self.StdData.arrTNAM)
    #
    #             pass
    #         elif mission == 2:
    #             # 切换文件
    #             pass
    #         elif mission == 3:
    #             pass
    #         if sendMsg is not None:
    #             if parameter_index in [1, 4, 12]:
    #                 self.fyCanSendData(sendMsg)
    #             if parameter_index < 9:
    #                 time.sleep(0.05)
    #                 self.fySendDelayAndWaitACK(msg=parameter_array)
    #             elif 9 <= parameter_index < 12:
    #                 self.fySendDelayAndWaitACK(msg=sendMsg)
    #         else:
    #             return False
    #     # 处理其他设备状态
    #     showErrorDialog(None, 'Machine Status Error.')
    #     self.trans_status(self.MachineStatus.Ready)
    #     return self.fySetCameraParameter(parameter_array, parameter_index)

    def fySetCameraParameter(self, parameter_array, parameter_index):
        num_array = [0x00, 0x31, 0x32, 0x33, 0x34]
        # 检查设备状态
        if not self.fyCheckSlaveStatus():
            return False
        # 处理设备状态为 Ready
        if self.__selfStatus == self.MachineStatus.Ready:
            rec_msg, rec_flag = self.fySendDataAndWait(message=self.StdData.arrRE2ED)
            if rec_flag:
                return self.fySetCameraParameter(parameter_array, parameter_index)
            return True
        # 处理设备状态为 Edit
        if self.__selfStatus == self.MachineStatus.Edit:
            sendMsg = self.getSendMsgByIndex(parameter_index, num_array)
            if sendMsg is not None:
                if parameter_index in [1, 4, 12]:
                    self.fyCanSendData(sendMsg)
                if parameter_index < 9:
                    time.sleep(0.05)
                    self.fySendDelayAndWaitACK(msg=parameter_array)
                elif 9 <= parameter_index < 12:
                    self.fySendDelayAndWaitACK(msg=sendMsg)
            else:
                return False
        # 处理其他设备状态
        showErrorDialog(None, 'Machine Status Error.')
        self.trans_status(self.MachineStatus.Ready)
        return self.fySetCameraParameter(parameter_array, parameter_index)

    def getSendMsgByIndex(self, parameter_index, num_array):
        """根据参数索引获取发送消息"""
        if parameter_index < 4:
            return self.StdData.arrS2ROI1
        elif 4 <= parameter_index <= 8:
            return self.StdData.arrS2CAM1
        elif 9 <= parameter_index < 12:
            sendMsg = self.StdData.arrS2MODE
            sendMsg[5] = num_array[parameter_index - 8]
            return sendMsg
        elif parameter_index == 12:
            return self.StdData.arrS2NAME
        else:
            return None

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
        if self.fyCheckSlaveStatus():
            if self.__selfStatus == self.MachineStatus.Ready:
                rec_msg, rec_flag = self.fySendDataAndWait(message=self.StdData.arrRE2AC)
                if compare_arr_ctypes_(input_arr=rec_msg, target_arr=self.StdData.arrPCO):
                    print('AC:下位机处于PCO')
                    self.fySendDelayData(self.StdData.arrACK, delay_time=10)
                    if self.fyCheckSlaveStatus():
                        if self.__selfStatus == self.MachineStatus.Activity:
                            print('下位机状态已经是Activity')
                            self.fySendDelayData(self.StdData.arrDetect, delay_time=1000)
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
                showErrorDialog(None, 'Machine Status Error.')
                self.trans_status(self.MachineStatus.Ready)
                self.fyStartDetect()
        else:
            return False

    # 检测停止
    def fyStopDetect(self):
        self.stop_processing_thread(1)
        self.fySendDelayData(self.StdData.arrEND, delay_time=1000)

    def fyReceiveImage(self):
        if self.fyCheckSlaveStatus():
            if self.__selfStatus == self.MachineStatus.Ready:
                rec_msg, rec_flag = self.fySendDataAndWait(message=self.StdData.arrRE2PC)
                if compare_arr_ctypes_(input_arr=rec_msg, target_arr=self.StdData.arrPCO):
                    print('PIC:下位机处于PCO')
                    self.fySendDelayData(self.StdData.arrACK, delay_time=10)
                    if self.fyCheckSlaveStatus():
                        if self.__selfStatus == self.MachineStatus.PIC:
                            print('下位机状态已经是PIC')
                            self._recImageSaveArr.clear()
                            self.__recMsgFinishIndex = 0
                            len_msg, rec_flag = self.fySendDataAndWait(message=self.StdData.arrSTA)
                            self.__recPicAllSize = calNumberArray(len_msg)
                            self.__recPicCurrentSize = 0
                            self.sig_progressValue.emit(0)
                            self.sig_canStatus.emit(False, 1)
                            self.__recImageFlag = True
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
                self.__recImageFlag = True
                self._recImageSaveArr = []
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
        if self.fyCheckSlaveStatus():
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
    def run(self):
        while not self.isInterruptionRequested():
            if self.floating_yarn:
                self.floating_yarn.can_receive_msg_2()
                with QMutexLocker(self.mutex):
                    if self.floating_yarn._recMsgSaveArr:
                        self.wait_condition.wakeAll()  # 唤醒处理线程
            else:
                QThread.msleep(100)  # 延时，以避免占用过多 CPU 资源


class CanProcessorThread(FYCanThread):
    def run(self):
        if self.floating_yarn is not None:
            while not self.isInterruptionRequested():
                with QMutexLocker(self.mutex):
                    while not self.floating_yarn._recImageSaveArr and not self.isInterruptionRequested():
                        self.wait_condition.wait(self.mutex)  # 等待数据到达
                    if self.isInterruptionRequested():
                        break

                    if self.floating_yarn._recImageSaveArr:
                        data_list = self.floating_yarn._recImageSaveArr[-1]
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
            sendRow = self.floating_yarn.__knitRow
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
