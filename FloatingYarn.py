from collections import deque
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
        self.received_image_arr = []
        self.received_image_flag = False
        self.__selfStatus = self.MachineStatus.Close
        self.__selfOperateMode = self.MachineOperate.Detect
        self.__canID = Can_id
        self.__canBaudRate = 1000
        self.__recMsgFinishIndex = 0

        # 启动接收线程
        self.wait_condition = QWaitCondition()
        self.mutex = QMutex()
        self.receiver_thread = CanReceiverThread(wait_condition=self.wait_condition, mutex=self.mutex)
        self.receiver_thread.set_floating_yarn(self)
        self.receiver_thread.start()

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
        rec_msg,rec_flag = self.fySendDataAndWait(message=self.StdData.arrSTATUS, timeout_ms=1000,backToACK=False)
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

    # 检查结束符号
    def detectSpecificCharacters(self, data_list):
        if self.__recMsgFinishIndex == 8:
            self.__recMsgFinishIndex = 0
            self.received_image_flag = False
            print("图片接收完成")
        for data in data_list:
            if data == self.StdData.arrMSG_FINISH[self.__recMsgFinishIndex]:
                self.__recMsgFinishIndex = self.__recMsgFinishIndex + 1
            else:
                self.__recMsgFinishIndex = 0

    def receiving_msg_processing(self, vci_can_obj):
        data_list = list(vci_can_obj.Data)
        self.received_messages.append(data_list)
        if self.received_messages:
            self.wait_condition.wakeAll()
            if self.received_image_flag:
                self.received_image_arr.append(self.received_messages[-1])
                self.detectSpecificCharacters(self.received_messages[-1])
            else:
                self.message_received.emit(list_to_str(self.received_messages[-1]))  # 发送信号

    def fy_canSendData(self, send_data):
        self.change_send_data(send_data)
        self.can_send_msg()

    # 发送数据并等待接收
    def fySendDataAndWait(self, message, timeout_ms=50000, backToACK=False):
        """发送数据并等待接收，带超时机制"""
        self.fy_canSendData(message)

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
        else:
            if backToACK:
                self.fy_canSendData(self.StdData.arrACK)

        # 返回接收到的数据和成功标志
        if self.received_messages:
            return self.received_messages[-1], True
        else:
            return None, False

    def fy_receive_image(self):
        if self.checkSlaveStatus():
            if self.__selfStatus == self.MachineStatus.Ready:
                rec_msg,rec_flag = self.fySendDataAndWait(message=self.StdData.arrRE2PC, backToACK=True)
                if compare_arr_ctypes_(input_arr=rec_msg, target_arr=self.StdData.arrPCO):
                    print('下位机处于PCO')
                    self.received_image_flag = True
                    self.received_image_arr = []
                    self.__recMsgFinishIndex = 0
                    self.fy_canSendData(self.StdData.arrSTA)
                    return True
                elif compare_arr_ctypes_(input_arr=rec_msg, target_arr=self.StdData.arrPCC):
                    print('下位机处于PCC')
                    self.fy_receive_image()
                    return True
            elif self.__selfStatus == self.MachineStatus.PIC:
                self.received_image_flag = True
                self.received_image_arr = []
                self.__recMsgFinishIndex = 0
                self.fy_canSendData(self.StdData.arrSTA)
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
        while True:
            if self.floating_yarn:
                self.floating_yarn.can_receive_msg()
                with QMutexLocker(self.mutex):
                    if self.floating_yarn.received_messages:
                        self.wait_condition.wakeAll()  # 唤醒等待线程
            else:
                # 如果 floating_yarn 还没有设置好，稍作等待
                QThread.msleep(100)  # 暂时的延时，以避免占用过多 CPU 资源


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
