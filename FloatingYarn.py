import binascii
from collections import deque
from ctypes import byref
from enum import Enum

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QThread, QMutex, QTimer, QWaitCondition, QMutexLocker, \
    QEventLoop
from PyQt5.QtWidgets import QApplication, QWidget, QListWidget, QVBoxLayout, QTextEdit, QPushButton, QMainWindow, \
    QMessageBox

from CANMessageData import CANMessageData
from Can_Derive import Can_Derive
import sys
from datetime import datetime


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
    message_received = pyqtSignal(str)

    class MachineStatus(Enum):
        Close = 0
        Open = 1
        Ready = 2
        Activate = 3
        Edit = 4
        PIC = 5

    class MachineOperate(Enum):
        Detect = 0
        Compare = 1
        Record = 2

    def __init__(self, win_linux=1, Can_id=0x141, max_messages=10000):
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
        self.__recMsgFinishIndex = 0
        self.__msgFinishArray = [8, 9, 10, 11, 12, 13, 14, 15]
        self.__msgStartArray = [0, 1, 2, 3, 4, 5, 6, 7]

        # 启动接收线程
        self.wait_condition = QWaitCondition()
        self.mutex = QMutex()

        # 启动接收线程
        self.receiver_thread = CanReceiverThread(wait_condition=self.wait_condition, mutex=self.mutex)
        self.receiver_thread.set_floating_yarn(self)
        self.receiver_thread.start()

        self.processor_thread = None

    def start_processing_thread(self):
        # 启动处理线程
        self.processor_thread = CanProcessorThread(wait_condition=self.wait_condition, mutex=self.mutex)
        self.processor_thread.set_floating_yarn(self)
        self.processor_thread.start()

    def stop_processing_thread(self):
        if self.processor_thread is not None:
            self.processor_thread.requestInterruption()  # 触发线程停止
            self.processor_thread.wait()  # 等待线程结束
            self.processor_thread = None

    # 检查结束符号
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
                            self.fyCanSendData(self.StdData.arrEND)
                            self.stop_processing_thread()  # 停止处理线程
                            print("图片接收完成")
                            self.dequeToImage()  # 转换数据为图片
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
        # 处理图像数据
        while True:
            if not self.received_image_arr:
                print("图像数据处理完成")
                break  # 如果 deque 为空，退出循环

            data_list = self.received_image_arr.popleft()
            # 将 data_list 中的每个字节直接追加到 image_array
            for dec_data in data_list:
                hex_str = hex_str + hex(dec_data)[2:].upper() + " "

        output_file_path = 'rec_txt/hex_output.txt'
        with open(output_file_path, 'w') as file:
            file.write(hex_str.strip())  # 使用 strip() 去掉最后多余的空格

        print(f'Hex string saved to {output_file_path}')
        # 保存为图片
        # byte_array = binascii.unhexlify(hex_str)
        # output_image_path = 'rec_txt/output_image.jpg'
        # with open(output_image_path, 'wb') as image_file:
        #     image_file.write(byte_array)
        #
        # print(f'图像已保存到 {output_image_path}')

    def receiving_msg_processing(self, vci_can_obj):
        data_list = list(vci_can_obj.Data)
        with QMutexLocker(self.mutex):  # 确保线程安全
            if self.received_image_flag:
                # print(data_list)  # 直接输出接收到的数据
                self.received_image_arr.append(data_list)
                if not self.processor_thread:
                    self.start_processing_thread()  # 开始处理线程
            else:
                self.received_messages.append(data_list)
                self.wait_condition.wakeAll()  # 唤醒等待的线程
                # 发射信号，确保在主线程中
                self.message_received.emit(list_to_str(data_list))

    # CAN关启动
    def fyCanOpen(self, canBaud=1000):
        self.can_init()
        self.can_channel_open(baud=canBaud)
        if self.check_CAN_STATUS():
            return True
        else:
            return False

    # CAN关闭
    def fyCanClose(self):
        self.can_close()

    # 下位机运行状态检查
    def checkSlaveStatus(self):
        rec_msg, rec_flag = self.fySendDataAndWait(message=self.StdData.arrSTATUS, timeout_ms=1000)
        if rec_flag:
            if rec_msg[2] == 49:
                self.__selfStatus = self.MachineStatus.Open
            elif rec_msg[2] == 50:
                self.__selfStatus = self.MachineStatus.Ready
            elif rec_msg[2] == 51:
                self.__selfStatus = self.MachineStatus.Activate
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
            return True
        else:
            print("Failed to receive message.")
            return False

    def fyCanSendData(self, send_data):
        self.change_send_data(send_data)
        self.can_send_msg()

    def fyDelaySendData(self, msg, delay_time=10):
        QTimer.singleShot(delay_time, lambda: self.fyCanSendData(msg))

        # 发送数据并等待接收

    def fySendDataAndWait(self, message, timeout_ms=50000):
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
            return self.received_messages[-1], True
        else:
            return None, False

    def fy_receive_image(self):
        if self.checkSlaveStatus():
            if self.__selfStatus == self.MachineStatus.Ready:
                rec_msg, rec_flag = self.fySendDataAndWait(message=self.StdData.arrRE2PC)
                if compare_arr_ctypes_(input_arr=rec_msg, target_arr=self.StdData.arrPCO):
                    print('下位机处于PCO')
                    self.fyDelaySendData(self.StdData.arrACK, delay_time=10)
                    if self.checkSlaveStatus():
                        if self.__selfStatus == self.MachineStatus.PIC:
                            print('下位机状态已经是PIC')
                            # self.received_image_arr.clear()
                            self.__recMsgFinishIndex = 0
                            self.fyDelaySendData(self.StdData.arrSTA, delay_time=1000)
                            self.received_image_flag = True

                            return True
                        else:
                            return False
                    else:
                        return False
                elif compare_arr_ctypes_(input_arr=rec_msg, target_arr=self.StdData.arrPCC):
                    print('下位机处于PCC')
                    self.fy_receive_image()
                    return True
            elif self.__selfStatus == self.MachineStatus.PIC:
                self.received_image_flag = True
                self.received_image_arr = []
                self.__recMsgFinishIndex = 0
                self.fyCanSendData(self.StdData.arrSTA)
                return True
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
                elif target_status == self.MachineStatus.Activate:
                    self.change_send_data(self.StdData.arrRE2AC)
                else:
                    return -1
            elif self.__selfStatus == self.MachineStatus.Edit:
                if target_status == self.MachineStatus.Ready:
                    self.change_send_data(self.StdData.arrBA2RE)
                else:
                    return -1
            elif self.__selfStatus == self.MachineStatus.Activate:
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
            self.can_send_msg(send_id=self.__canID)
            return 1
        else:
            return -2


class CanReceiverThread(QThread):
    """线程用于接收数据"""

    def __init__(self, wait_condition, mutex):
        super().__init__()
        self.floating_yarn = None  # 将在外部设置
        self.wait_condition = wait_condition
        self.mutex = mutex

    def set_floating_yarn(self, floating_yarn):
        self.floating_yarn = floating_yarn

    def run(self):
        while not self.isInterruptionRequested():
            if self.floating_yarn:
                self.floating_yarn.can_receive_msg_2()
                with QMutexLocker(self.mutex):
                    if self.floating_yarn.received_messages:
                        self.wait_condition.wakeAll()  # 唤醒处理线程
            else:
                QThread.msleep(100)  # 延时，以避免占用过多 CPU 资源


class CanProcessorThread(QThread):
    """线程用于处理数据"""

    def __init__(self, wait_condition, mutex):
        super().__init__()
        self.wait_condition = wait_condition
        self.mutex = mutex
        self.floating_yarn = None  # 将在外部设置

    def set_floating_yarn(self, floating_yarn):
        self.floating_yarn = floating_yarn

    def run(self):
        while not self.isInterruptionRequested():
            with QMutexLocker(self.mutex):
                while not self.floating_yarn.received_image_arr and not self.isInterruptionRequested():
                    self.wait_condition.wait(self.mutex)  # 等待数据到达

                if self.isInterruptionRequested():
                    break

                if self.floating_yarn.received_image_arr:
                    data_list = self.floating_yarn.received_image_arr[-1]
                    if data_list:
                        self.floating_yarn.detectSpecificCharacters(data_list=data_list,
                                                                    target_list=[8, 9, 10, 11, 12, 13, 14, 15])


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
        self.floating_yarn.message_received.connect(self.display_message)
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
