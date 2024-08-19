from PyQt5.QtWidgets import QDialog

from sql_dialog import Ui_Dialog


class SQLDialog(QDialog, Ui_Dialog):
    def __init__(self, parent=None, floating_yarn=None):
        super(SQLDialog, self).__init__(parent)
        self.setupUi(self)
        self.floating_yarn = floating_yarn

        self.pushButton_loadSqlData.clicked.connect(self.loadSqlData)
        self.pushButton_togglaSqlData.clicked.connect(self.toggleSqlData)
        self.pushButton_delectSqlData.clicked.connect(self.deleteSqlData)

    def loadSqlData(self):
        # 实现读取数据的逻辑
        self.floating_yarn.sqlDataLoad()

    def toggleSqlData(self):
        # 实现切换数据的逻辑
        self.floating_yarn.sqlDatatoggle()

    def deleteSqlData(self):
        # 实现删除数据的逻辑
        self.floating_yarn.sqlDatadelect()
