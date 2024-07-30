import sys

from PyQt5.QtWidgets import QApplication, QMainWindow


import candriver_layout
from FloatingYarn import FloatingYarn

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 初始化 FloatingYarn 实例
    # floating_yarn = FloatingYarn()

    # 将 FloatingYarn 实例传递给 MainWindow
    MainWindow = QMainWindow()
    ui = candriver_layout.Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())