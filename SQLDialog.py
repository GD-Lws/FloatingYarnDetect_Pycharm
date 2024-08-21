import string
import time

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QMessageBox, QListWidgetItem, QRadioButton, QTableWidgetItem

from sql_dialog_layout import Ui_Dialog


class SQLDialog(QDialog, Ui_Dialog):
    sig_filename = pyqtSignal(str)

    def __init__(self, parent=None, floating_yarn=None):
        super(SQLDialog, self).__init__(parent)
        self.setupUi(self)
        self.floating_yarn = floating_yarn

        self.pushButton_loadSqlData.clicked.connect(self.loadSqlData)
        self.pushButton_togglaSqlData.clicked.connect(self.toggleSqlData)
        self.pushButton_dropSqlData.clicked.connect(self.dropSqlData)
        self.pushButton_dropSqlAllData.clicked.connect(self.dropSqlAllData)
        self.floating_yarn.sig_sqlTableNameList.connect(self.addItems2Table)

    def loadSqlData(self):
        # 实现读取数据的逻辑
        self.floating_yarn.fyTrans2Ready()
        time.sleep(0.05)
        self.floating_yarn.fySetSQLState(mission=1)
        time.sleep(0.05)
        self.floating_yarn.fyTrans2Ready()

    def toggleSqlData(self):
        # 实现切换数据的逻辑
        selectArray = self.getSelectedRadioButtonFromTable()
        if len(selectArray):
            for data in selectArray:
                self.floating_yarn.fySetSQLState(mission=2, byteName=data)
            self.floating_yarn.fyTrans2Ready()
            self.sig_filename.emit(selectArray[0])

    def addItems2Table(self, data_list):
        # 确保表格的列数和标题设置正确
        self.tableWidget_recTab.setColumnCount(3)
        self.tableWidget_recTab.setHorizontalHeaderLabels(["序号", "表名", "选择"])
        # 设置行数
        self.tableWidget_recTab.setRowCount(len(data_list))
        # 填充数据
        for row, data in enumerate(data_list):
            if row == 0:
                # 对于第一行，显示总数
                index_item = QTableWidgetItem("Len")
                self.tableWidget_recTab.setItem(row, 0, index_item)
                data_item = QTableWidgetItem(data)
                self.tableWidget_recTab.setItem(row, 1, data_item)
            else:
                # 创建单选框并设置到第三列
                radio_button = QRadioButton()
                self.tableWidget_recTab.setCellWidget(row, 2, radio_button)
                # 创建序号列，序号从1开始
                index_item = QTableWidgetItem(str(row))
                self.tableWidget_recTab.setItem(row, 0, index_item)
                # 填充数据列
                data_item = QTableWidgetItem(data)
                self.tableWidget_recTab.setItem(row, 1, data_item)

    def dropSqlData(self):
        # 实现删除数据的逻辑
        if self.show_confirm_dialog():
            selectArray = self.getSelectedRadioButtonFromTable()
            if len(selectArray):
                for data in selectArray:
                    self.floating_yarn.fySetSQLState(mission=3, byteName=data)
                time.sleep(0.05)
                self.loadSqlData()
                time.sleep(0.05)
                self.floating_yarn.fyTrans2Ready()

    def dropSqlAllData(self):
        # 实现删除数据的逻辑
        if self.show_confirm_dialog():
            self.floating_yarn.fySetSQLState(mission=4)
            time.sleep(0.05)
            self.loadSqlData()
            time.sleep(0.05)
            self.floating_yarn.fyTrans2Ready()

    def show_confirm_dialog(self):
        # 创建一个QMessageBox
        confirm_dialog = QMessageBox(self)
        confirm_dialog.setWindowTitle("确认")
        confirm_dialog.setText("你确定要执行此操作吗？")
        confirm_dialog.setIcon(QMessageBox.Question)
        confirm_dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm_dialog.setDefaultButton(QMessageBox.No)

        # 显示确认窗口并获取用户的选择
        result = confirm_dialog.exec_()

        if result == QMessageBox.Yes:
            return True
        else:
            return False

    def getSelectedRadioButtonFromTable(self):
        selected_filename = []
        for row in range(self.tableWidget_recTab.rowCount()):
            radio_button = self.tableWidget_recTab.cellWidget(row, 2)
            if radio_button and radio_button.isChecked():
                # 获取第二列（文件名列）的文件名
                filename_item = self.tableWidget_recTab.item(row, 1)
                if filename_item:
                    selected_filename.append(filename_item.text())
                break  # 找到选中的单选框后退出循环
        return selected_filename
