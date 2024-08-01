import sys

from PyQt5.QtWidgets import QApplication, QMainWindow
import candriver_layout
from FloatingYarn import FloatingYarn

floatingYarn = None
qtUI = None


class ListWidgetPrinter:
    def __init__(self, list_widget):
        self.list_widget = list_widget

    def write(self, message):
        if message:  # 忽略空消息
            self.list_widget.addItem(message.strip())  # 添加到 QListWidget 中

    def flush(self):
        pass  # Flush 方法用于兼容 Python 的 I/O 接口


# 按键初始化关联函数
class MainWindow:
    def __init__(self):
        self.app = QApplication(sys.argv)

        # 初始化 FloatingYarn 实例
        self.floating_yarn = FloatingYarn()
        self.MainWindow = QMainWindow()
        # 初始化 UI 管理器并设置连接
        self.ui_manager = candriver_layout.Ui_MainWindow()
        self.ui_manager.setupUi(self.MainWindow)
        # self.printer = ListWidgetPrinter(self.ui_manager.listWidget_log)
        # sys.stdout = self.printer  # 重定向 print 到 ListWidgetPrinter
        self.uiConnectInit()

    def run(self):
        self.MainWindow.show()
        sys.exit(self.app.exec_())

    def uiComboBoxInit(self):
        self.ui_manager.comboBox_baudRate.addItems(["100kbps", "500kbps", "1000kbps"])
        self.ui_manager.comboBox_ModeSelect.addItems(["Detect", "Compare", "Record"])

    def uiCanOpen(self):
        index = self.ui_manager.comboBox_baudRate.currentIndex()
        baud_rates = [1000, 500, 100]
        if 0 <= index < len(baud_rates):
            baud_rate = baud_rates[index]
            self.floating_yarn.__canBaudRate = baud_rate
            self.floating_yarn.fyCanOpen(canBaud=baud_rate)

    # 将接收到的数据添加到列表
    def displayRecMessage(self, msg):
        self.ui_manager.listWidget_rec.addItem(msg)

    def uiConnectInit(self):
        self.uiComboBoxInit()
        self.ui_manager.button_driver_connect.clicked.connect(self.uiCanOpen)
        self.ui_manager.button_driver_disconnect.clicked.connect(self.floating_yarn.fyCanClose)
        self.ui_manager.button_getImage.clicked.connect(self.floating_yarn.fy_receive_image)
        self.floating_yarn.message_received.connect(self.displayRecMessage)
        self.ui_manager.button_GetStatus.clicked.connect(self.floating_yarn.checkSlaveStatus)


if __name__ == "__main__":
    main_window = MainWindow()
    main_window.run()
