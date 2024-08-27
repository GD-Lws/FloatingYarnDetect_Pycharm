import ctypes
import sys
import time

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsPixmapItem, QGraphicsScene, QInputDialog, QMessageBox
from pyqt5_plugins.examplebutton import QtWidgets

import candriver_layout
from FloatingYarn import FloatingYarn, numValue2CtypeArray, strValue2CtypeArray
from SQLDialog import SQLDialog

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
def combine_arrays(array1, array2):
    """将两个固定长度的字节数组合并为一个 ctypes 数组"""
    combined_array = (ctypes.c_uint8 * 8)()
    for i in range(4):
        combined_array[i] = array1[i]
        combined_array[i + 4] = array2[i]
    return combined_array


class MainWindow:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.image_path = 'rec_txt/output_image.jpg'
        # 初始化 FloatingYarn 实例
        self.floating_yarn = FloatingYarn(temp_photo_storage_path=self.image_path)
        self.MainWindow = QMainWindow()
        # 初始化 UI 管理器并设置连接
        self.ui_manager = candriver_layout.Ui_MainWindow()
        self.ui_manager.setupUi(self.MainWindow)
        self.printer = ListWidgetPrinter(self.ui_manager.listWidget_log)
        self.sqlDialog = SQLDialog(floating_yarn=self.floating_yarn)
        sys.stdout = self.printer  # 重定向 print 到 ListWidgetPrinter
        self.uiConnectInit()
        self.setTheUIDefaultValue()

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

    def roiParameterSet(self, roi_params):
        roi_arrays = [numValue2CtypeArray(param, length=4) for param in roi_params]
        self.floating_yarn.fyTrans2Ready()
        # 组合数组并设置相机参数
        for i in range(4):
            combined_array = combine_arrays(roi_arrays[i * 2], roi_arrays[i * 2 + 1])
            self.floating_yarn.fySetCameraParameter(combined_array, i)
            time.sleep(0.05)
        self.showInfoDialog("设置识别区域成功")

    def cameraParameterSet(self):
        self.uiSetButtonStatus(False, 1)
        self.floating_yarn.fyTrans2Ready()
        # 注意顺序不能改动ET->ISO->FD->ZR
        camera_params = [
            self.ui_manager.edit_par_ExposureTime.text().replace("\x00", ""),
            self.ui_manager.edit_par_ISO.text().replace("\x00", ""),
            self.ui_manager.edit_par_focusDis.text().replace("\x00", ""),
            self.ui_manager.edit_par_ZoomRatio.text().replace("\x00", "")
        ]
        camera_arrays = [numValue2CtypeArray(param, length=8) for param in camera_params]
        for i in range(4):
            self.floating_yarn.fySetCameraParameter(camera_arrays[i], i + 4)
            time.sleep(0.05)
        self.showInfoDialog("设置参数成功")
        self.uiSetButtonStatus(True, 0)

    def comboxDetectModeChange(self, index):
        camera_array = (ctypes.c_uint8 * 8)()
        self.floating_yarn.fySetCameraParameter(camera_array, index + 8)
        self.floating_yarn.fyTrans2Ready()
        self.floating_yarn.fyCheckSlaveStatus()
        if index == 2:
            text, ok = QInputDialog.getText(self.MainWindow, 'Input Dialog', 'Enter Target Table name:')
            if ok:
                if len(text) > 7:
                    text = text[:8]  # 截断输入
                    print('输入过长，已截断为:', text)
                    # 可选：显示一个警告或信息框
                    QMessageBox.warning(self.MainWindow, '输入警告', '输入的目标表名过长，已自动截断。')
                else:
                    print('User input:', text)
                self.updateFileName(text)
                # self.setUpFileName(filename=text)

    def roi1ParameterSet(self):
        """设置ROI1参数"""
        roi_params = [
            self.ui_manager.edit_roiRange1_x1.text().strip(),
            self.ui_manager.edit_roiRange1_y1.text().strip(),
            self.ui_manager.edit_roiRange1_x2.text().strip(),
            self.ui_manager.edit_roiRange1_y2.text().strip(),
            self.ui_manager.edit_roiRange2_x1.text().strip(),
            self.ui_manager.edit_roiRange2_y1.text().strip(),
            self.ui_manager.edit_roiRange2_x2.text().strip(),
            self.ui_manager.edit_roiRange2_y2.text().strip(),
        ]
        self.roiParameterSet(roi_params)

    def setTheUIDefaultValue(self):
        # 假设 self.ui_manager 是一个包含 QLineEdit 对象的 UI 管理器
        self.ui_manager.edit_roiRange1_x1.setText('512')
        self.ui_manager.edit_roiRange1_y1.setText('200')
        self.ui_manager.edit_roiRange1_x2.setText('512')
        self.ui_manager.edit_roiRange1_y2.setText('380')
        self.ui_manager.edit_roiRange2_x1.setText('512')
        self.ui_manager.edit_roiRange2_y1.setText('400')
        self.ui_manager.edit_roiRange2_x2.setText('662')
        self.ui_manager.edit_roiRange2_y2.setText('580')

        self.ui_manager.edit_par_ExposureTime.setText('7104250')
        self.ui_manager.edit_par_ISO.setText('1200')
        self.ui_manager.edit_par_focusDis.setText('4.12')
        self.ui_manager.edit_par_ZoomRatio.setText('1.0')
        self.ui_manager.progressBar_piccture.setValue(0)
        font = self.ui_manager.label_detect_flag.font()  # 获取当前的字体
        font.setPointSize(12)  # 设置新的字体大小
        self.ui_manager.label_detect_flag.setFont(font)  # 应用新的字体
        self.ui_manager.label_detect_flag.setText('Detection not started')

        self.uiSetButtonStatus(False, 0)

    def uiConnectInit(self):
        self.uiComboBoxInit()
        self.ui_manager.button_driver_connect.clicked.connect(self.uiCanOpen)
        self.ui_manager.button_roiRange.clicked.connect(self.roi1ParameterSet)
        self.ui_manager.button_filenameSet.clicked.connect(self.buttonSetFileName)
        self.ui_manager.button_clearmsg.clicked.connect(self.clearListMsg)
        self.ui_manager.button_parSet.clicked.connect(self.cameraParameterSet)
        # self.ui_manager.button_ge

        self.ui_manager.button_driver_disconnect.clicked.connect(self.floating_yarn.fyCanClose)
        self.ui_manager.button_getImage.clicked.connect(self.floating_yarn.fyReceiveImage)
        self.ui_manager.button_GetStatus.clicked.connect(self.floating_yarn.fyCheckSlaveStatus)
        self.ui_manager.button_ReadyStatus.clicked.connect(self.floating_yarn.fyTrans2Ready)
        self.ui_manager.button_stopimage.clicked.connect(self.floating_yarn.fyStopImageRec)
        self.ui_manager.button_startdetect.clicked.connect(self.floating_yarn.fyStartDetect)
        self.ui_manager.button_stopdetect.clicked.connect(self.floating_yarn.fyStopDetect)
        self.ui_manager.button_SQLShow.clicked.connect(self.openSqlDialog)
        self.ui_manager.button_parGet.clicked.connect(self.getCameraParams)

        self.ui_manager.comboBox_ModeSelect.currentIndexChanged.connect(self.comboxDetectModeChange)

        self.floating_yarn.sig_imageProcess.connect(self.loadImageFromCurrentDirectory)
        self.floating_yarn.sig_messageReceived.connect(self.displayRecMessage)
        self.floating_yarn.sig_statusUpdated.connect(self.updateFyStatus)
        self.floating_yarn.sig_progressValue.connect(self.updateProgressBar)
        self.floating_yarn.sig_canStatus.connect(self.uiSetButtonStatus)
        self.floating_yarn.sig_cameraPar.connect(self.getCameraParams2EditText)
        self.floating_yarn.sig_errorDialog.connect(self.showErrorDialog)
        self.floating_yarn.sig_infoDialog.connect(self.showInfoDialog)
        self.floating_yarn.sig_detectResult.connect(self.setDetectFlag)

        self.sqlDialog.sig_filename.connect(self.updateFileName)

    def updateFileName(self, filename):
        self.ui_manager.edit_par_FileName.setText(filename)

    def uiSetButtonStatus(self, status, index):
        button_list = [
            self.ui_manager.button_parSet,
            self.ui_manager.button_ReadyStatus,
            self.ui_manager.button_roiRange,
            self.ui_manager.button_getImage,
            self.ui_manager.button_GetStatus,
            self.ui_manager.button_stopimage,
            self.ui_manager.button_parGet,
            self.ui_manager.button_parSave,
            self.ui_manager.button_startdetect,
            self.ui_manager.button_stopdetect,
            self.ui_manager.button_Log,
            self.ui_manager.button_SQLShow,
            self.ui_manager.button_filenameSet,
        ]

        if 1 <= index < len(button_list) + 1:
            for button in button_list:
                button.setEnabled(not status)
            button_list[index - 1].setEnabled(status)
        elif index == 0:
            # 启用或禁用所有按钮
            for button in button_list:
                button.setEnabled(status)
        else:
            print(f"Index {index} is out of range.")

    # 加载图片从文件路径
    def loadImageFromCurrentDirectory(self):
        # 构造图片的相对路径
        # 加载图片
        scene = QtWidgets.QGraphicsScene()
        pixmap = QPixmap(self.image_path)
        # 创建 QGraphicsPixmapItem 并设置其缩放
        pixmap_item = QGraphicsPixmapItem(pixmap)
        pixmap_item.setTransformationMode(Qt.SmoothTransformation)  # 平滑缩放

        # 旋转图片（以90度为例）
        rotation_angle = 90  # 你可以根据需要调整角度
        pixmap_item.setRotation(rotation_angle)

        if pixmap.isNull():
            print(f"Failed to load image from {self.image_path}")
            return
        view = self.ui_manager.GraphView_Image
        view_rect = view.viewport().rect()
        pixmap_size = pixmap.size()
        scale_x = view_rect.width() / pixmap_size.width()
        scale_y = view_rect.height() / pixmap_size.height()
        scale = min(scale_x, scale_y)  # 选择适应视图的最大缩放因子

        pixmap_item.setScale(scale * 1.5)

        # 清除之前的内容并添加新图片
        scene.clear()
        scene.addItem(pixmap_item)

        # 设置场景到视图
        view.setScene(scene)
        view.setSceneRect(scene.itemsBoundingRect())  # 设置场景的矩形

    def setDetectFlag(self, recRow):
        self.ui_manager.label_detect_flag.setText(recRow)

    # 更新下位机状态
    def updateFyStatus(self, status, mode):
        self.ui_manager.label_stateshow.setText(status.replace("MachineStatus", "状态:"))
        self.ui_manager.label_operatemode.setText(mode.replace("MachineOperate", "模式:"))

    # 更新接收照片进度条
    def updateProgressBar(self, progress):
        self.ui_manager.progressBar_piccture.setValue(progress)

    def clearListMsg(self):
        self.ui_manager.listWidget_log.clear()
        self.ui_manager.listWidget_rec.clear()

    def buttonSetFileName(self):
        self.uiSetButtonStatus(False, 13)
        filename = self.ui_manager.edit_par_FileName.text()
        # 检查文件名是否以数字开头
        if filename and filename[0].isdigit():
            # 自动添加前缀，如 "_"，也可以提示用户重新输入
            filename = "_" + filename
            self.updateFileName(filename)
            # 提示用户
            QtWidgets.QMessageBox.warning(self.MainWindow, "文件名错误", "文件名不能以数字开头，已自动添加前缀 '_'。")
        # 继续设置文件名
        self.setUpFileName(filename)
        self.uiSetButtonStatus(True, 0)

    def setUpFileName(self, filename):
        filename_array = strValue2CtypeArray(filename, length=8)
        self.floating_yarn.fyTrans2Ready()
        self.floating_yarn.fySetCameraParameter(filename_array, 11)
        self.floating_yarn.fyTrans2Ready()

    def getCameraParams(self):
        self.uiSetButtonStatus(False, 7)
        self.floating_yarn.fyTrans2Ready()
        self.floating_yarn.fySetCameraParameter(None, 12)

    # 设置编辑参数
    def getCameraParams2EditText(self, msgList):
        if len(msgList) != 12:
            return
        # 定义msgList与相应的UI控件之间的映射
        mapping = [
            (0, self.ui_manager.edit_par_focusDis),
            (1, self.ui_manager.edit_par_ISO),
            (2, self.ui_manager.edit_par_ExposureTime),
            (3, self.ui_manager.edit_par_ZoomRatio),
            (4, self.ui_manager.edit_roiRange1_x1),
            (5, self.ui_manager.edit_roiRange1_y1),
            (6, self.ui_manager.edit_roiRange1_x2),
            (7, self.ui_manager.edit_roiRange1_y2),
            (8, self.ui_manager.edit_roiRange2_x1),
            (9, self.ui_manager.edit_roiRange2_y1),
            (10, self.ui_manager.edit_roiRange2_x2),
            (11, self.ui_manager.edit_roiRange2_y2)
        ]

        # 循环设置文本
        for index, edit in mapping:
            edit.setText(msgList[index])
        self.uiSetButtonStatus(True, 0)

    def showErrorDialog(self, msg):
        QMessageBox.critical(self.MainWindow, 'Error', msg, QMessageBox.Ok)

    def showInfoDialog(self, msg):
        QMessageBox.information(self.MainWindow, 'Info', msg, QMessageBox.Ok)

    def openSqlDialog(self):
        self.sqlDialog.exec_()


if __name__ == "__main__":
    main_window = MainWindow()
    main_window.run()
