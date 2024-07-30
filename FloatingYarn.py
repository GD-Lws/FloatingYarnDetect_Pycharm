from collections import deque

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QThread, QMutex, QTimer, QWaitCondition, QMutexLocker, \
    QEventLoop
from PyQt5.QtWidgets import QApplication, QWidget, QListWidget, QVBoxLayout, QTextEdit, QPushButton, QMainWindow

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


def handle_timeout(event_loop):
    event_loop.quit()  # 退出事件循环


class FloatingYarn(Can_Derive, QObject):
    message_received = pyqtSignal(str)
    receive_timeout = pyqtSignal()  # 信号，用于通知接收超时

    def __init__(self, win_linux=1, send_id=0x141, max_messages=10000):
        QObject.__init__(self)
        Can_Derive.__init__(self, win_linux=win_linux)

        self.StdData = CANMessageData()
        self.can_init()
        self.can_channel_open()
        self.received_messages = deque(maxlen=max_messages)

        # 启动接收线程
        self.wait_condition = QWaitCondition()
        self.mutex = QMutex()
        self.receiver_thread = CanReceiverThread(wait_condition=self.wait_condition, mutex=self.mutex)
        self.receiver_thread.set_floating_yarn(self)
        self.receiver_thread.start()

    def receiving_msg_processing(self, vci_can_obj):
        data_list = list(vci_can_obj.Data)
        self.received_messages.append(data_list)
        if self.received_messages:
            self.message_received.emit(list_to_str(self.received_messages[-1]))  # 发送信号

    def fy_canSendData(self, send_data):
        self.change_send_data(send_data)
        self.can_send_msg()

    def send_data_and_wait(self, message, timeout_ms=5000):
        """发送数据并等待接收，带超时机制"""
        self.fy_canSendData(message)

        # 设置超时机制
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(self.on_timeout)
        timer.start(timeout_ms)

        # 使用 QWaitCondition 和 QMutex 进行同步
        with QMutexLocker(self.mutex):
            data_received = self.wait_condition.wait(self.mutex, timeout_ms)  # 等待接收数据或超时

        if not data_received:
            # 处理超时情况
            self.on_timeout()

    def on_timeout(self):
        """处理超时"""
        print("Timeout occurred. No response received.")
        self.receive_timeout.emit()  # 发射超时信号

    def handle_data_received(self, msg):
        """处理接收到的数据"""
        print(f"Data received: {msg}")
        self.fy_canSendData(msg)  # 处理接收到的数据


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


class MainWindow(QMainWindow):
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
        self.floating_yarn.receive_timeout.connect(self.display_timeout)
        self.floating_yarn.send_data_and_wait(self.floating_yarn.StdData.arrRE2PC)

    def display_message(self, msg):
        self.list_widget.addItem(msg)  # 将接收到的数据添加到列表

    def display_timeout(self):
        self.text_edit.append("Timeout occurred. No response received.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
