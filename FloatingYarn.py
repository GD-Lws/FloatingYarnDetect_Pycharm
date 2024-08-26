import ctypes
import time
from collections import deque
from datetime import datetime
from enum import Enum

from PyQt5.QtCore import pyqtSignal, QObject, QThread, QMutex, QTimer, QWaitCondition, QMutexLocker

from CAN_TOOL.CANMessageData import CANMessageData
from CAN_TOOL.Can_Derive import Can_Derive
from FYCanThread import FYCanThread


def numValue2CtypeArray(value_str, length=5):
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


# 十进制转Str
def decimal2String(decimal_values):
    # 将每个十进制数转换为对应的ASCII字符
    ascii_string = ''.join(chr(int(hex_value)) for hex_value in decimal_values)
    return ascii_string


# 字符串转ctype数组
def strValue2CtypeArray(value_str, length=8):
    ctype_array = (ctypes.c_uint8 * length)()
    for i, char in enumerate(value_str):
        if i < length:
            ctype_array[i] = ord(char)
    if len(value_str) < length:
        for i in range(len(value_str), length):
            ctype_array[i] = 0x00
    return ctype_array


# 计算图片数据长度
def calNumberArray(input_list):
    if len(input_list) != 8:
        return -1
    outputData = 0
    for i in range(8):
        data = input_list[i] - 48
        multiData = 10 ** (7 - i)
        outputData = outputData + data * multiData
    return outputData


# 接收数据转为str
def recList2Str(input_list, timeStamp=True):
    """将十进制 ASCII 列表转换为字符串，并附加接收时间戳"""
    message_str = ''
    if isinstance(input_list, list):
        try:
            # 将每个十进制数转换为 ASCII 字符
            message_str = ''.join(chr(value) for value in input_list)
        except ValueError:
            message_str = 'Invalid ASCII values'
    if timeStamp:
        # 获取当前时间戳
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 将时间戳添加到字符串末尾
        message_str += f' (Received at: {timestamp})'

    return message_str


# input_arr 是接收的数据
# 判断接收数据是否和目标数据相同
def compare_arr_ctypes_(input_arr, target_arr):
    arrTarget_int = [int(x) for x in target_arr]
    for i in range(8):
        if input_arr[i] != arrTarget_int[i]:
            return False
    return True


# 数据库反馈数据提取
def sqlListExtract(recList, startChar, endChar):
    ansList = []
    targetFlag = False

    for data in recList:
        if data == startChar:
            targetFlag = True
            continue
        if data == endChar:
            break
        if targetFlag:
            ansList.append(data)
    return ansList


class FloatingYarn(Can_Derive, QObject):
    # 接收信息信号
    sig_messageReceived = pyqtSignal(str)
    # 下位机状态更新
    sig_statusUpdated = pyqtSignal(str, str)
    # 照片传输完成
    sig_imageProcess = pyqtSignal()
    # 照片接收进度
    sig_progressValue = pyqtSignal(int)
    sig_canStatus = pyqtSignal(bool, int)
    # 数据库读取列表
    sig_sqlTableNameList = pyqtSignal(list)
    # 相机读取数据
    sig_cameraPar = pyqtSignal(list)
    # 错误信号窗口
    sig_errorDialog = pyqtSignal(str)
    # 提示信号窗口
    sig_infoDialog = pyqtSignal(str)
    # 检测结果信号
    sig_detectResult = pyqtSignal(str)

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
        self.__selfStatus = self.MachineStatus.Close
        self.__selfOperateMode = self.MachineOperate.Detect
        self.__canID = Can_id
        self.__canBaudRate = 1000
        self.__canStatus = False

        self.__recMsgFinishIndex = 0
        self.finishMsgArr = [8, 9, 10, 11, 12, 13, 14, 15]
        self.startMsgArr = [0, 1, 2, 3, 4, 5, 6, 7]
        self.__imageSavePath = temp_photo_storage_path

        # 同步锁
        self.__waitCondition = QWaitCondition()
        self.__Mutex = QMutex()

        # 启动接收线程
        self.__recMsgThread = CanReceiverThread(wait_condition=self.__waitCondition, mutex=self.__Mutex)
        self.__recMsgThread.set_floating_yarn(self)
        self.__recMsgThread.start()

        # 用于数据接收处理线程
        self.__processorThread = None
        # 用于持续发送当前编织行数
        self.knitRow = 0
        self.__sendKnitInfoThread = None

        self.__recPicAllSize = 0
        self.__recPicCurrentSize = 0
        self.recMsgSaveArr = deque(maxlen=max_messages)

        self.__recSqlTabNameFlag = False
        self.__recImageFlag = False
        self.__recCameraParamsFlag = False
        self._processFlag = False

        self.recProcessDataArr = deque()
        self.__calTime = 0

        self.detectFlag = False

    def onTimeout(self):
        """超时处理，弹出错误对话框"""
        print("Timeout occurred. No response received.")
        self.sig_errorDialog.emit('Timeout occurred. No response received.')  # None 为父窗口

    # 开始线程并带有定时器（当线程运行超过设定时间则停止线程）
    def startThreadWithTimer(self, thread_type, timeout=0):
        if thread_type == 0:
            thread = self.__processorThread
            thread_class = CanProcessorThread
        elif thread_type == 1:
            thread = self.__sendKnitInfoThread
            thread_class = KnitSendThread
        else:
            print("Invalid thread type!")
            return
        if thread is None:
            thread = thread_class(wait_condition=self.__waitCondition, mutex=self.__Mutex)
            thread.set_floating_yarn(self)
            thread.start()

            if thread_type == 0:
                self.__processorThread = thread
            elif thread_type == 1:
                self.__sendKnitInfoThread = thread
            # 设定超时定时器，以避免接收不到信息时线程不停止
            if timeout != 0:
                QTimer.singleShot(timeout, lambda: self.stopProcessingThread(thread_type))
        else:
            print(f"{thread_type} thread is running!")

    # 停止处理线程
    def stopProcessingThread(self, thread_type):
        if thread_type == 0 and self.__processorThread is not None:
            self.__processorThread.requestInterruption()
            self.__processorThread = None
            print('RecMsgProcess Thread Stop')
        elif thread_type == 1 and self.__sendKnitInfoThread is not None:
            self.__sendKnitInfoThread.requestInterruption()
            self.__sendKnitInfoThread = None
            print('Knit Thread Stop')
        else:
            print(f"{thread_type} thread is not running!")

    # 用于检测结果反馈
    def detectResultProcess(self, fatalist):
        if fatalist[0] == 0x4B:
            # 接收行数
            recRow = decimal2String(fatalist[1:7])
            if fatalist[4] == 0x38:
                recRow = recRow + ":False"
                self.sig_detectResult.emit(recRow)
            else:
                recRow = recRow + ":True"
                self.sig_detectResult.emit(recRow)
                self.sig_errorDialog.emit("检测到浮纱")

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
                            self.__recImageFlag = False
                            self.processDscImageFlag()
                        elif self.__recSqlTabNameFlag:
                            self.__recSqlTabNameFlag = False
                            self.processDscSQLFlag()
                        elif self.__recCameraParamsFlag:
                            self.__recCameraParamsFlag = False
                            self.processDscCameraFlag()
                        self.stopProcessingThread(0)
                        return True
                else:
                    # 匹配失败，重置计数
                    finish_count = 0
            else:
                # 数据不在目标序列中，重置计数
                finish_count = 0
        return False

    # 当检测到结束标识符后处理图片数据
    def processDscImageFlag(self):
        self.dequeToImage()  # 转换数据为图片
        self.fyCanSendData(self.StdData.arrEND)
        now = time.time()
        time_difference = now - self.__calTime
        self.__calTime = 0
        minutes, seconds = divmod(time_difference, 60)
        print(f"{minutes}分钟 {seconds}秒")
        self.sig_canStatus.emit(True, 0)
        self.sig_infoDialog.emit('图片接收成功')

    # 当检测到结束标识符后处理相机信息数据
    def processDscCameraFlag(self):
        recMsg = []
        while True:
            if not self.recProcessDataArr:
                print("没有找到起始标识符数组")
                return False
            data_list = self.recProcessDataArr.popleft()
            # 调用 detectSpecificCharacters 并检查是否找到 target_list
            if self.detectSpecificCharacters(data_list, target_list=[0, 1, 2, 3, 4, 5, 6, 7]):
                print("找到起始标识符数组")
                break  # 如果找到 target_list，退出循环
        # self.recProcessDataArr[-1]
        self.recProcessDataArr.pop()
        for data in self.recProcessDataArr:
            recMsg.append(decimal2String(data))
        self.sig_cameraPar.emit(recMsg)
        self.sig_infoDialog.emit('参数获取成功')

    # 当检测到结束标识符后处理数据库数据
    def processDscSQLFlag(self):
        if not self.recProcessDataArr:
            return  # 如果列表为空，则直接返回
        # 获取第一个元素的长度（假设它是长度数据）
        len_array = self.recProcessDataArr[0]
        print(recList2Str(len_array, False))
        sqlTableNameArr = []
        for recData in self.recProcessDataArr:
            extracted_data = sqlListExtract(recData, 58, 59)
            dataStr = recList2Str(extracted_data, timeStamp=False)
            if len(dataStr):
                sqlTableNameArr.append(dataStr)
        self.sig_sqlTableNameList.emit(sqlTableNameArr)

    def dequeToImage(self):
        print(len(self.recProcessDataArr))
        image_array = bytearray()  # 使用 bytearray 存储数据
        # 处理起始标识符
        while True:
            if not self.recProcessDataArr:
                print("没有找到起始标识符数组")
                return False
            data_list = self.recProcessDataArr.popleft()
            # 调用 detectSpecificCharacters 并检查是否找到 target_list
            if self.detectSpecificCharacters(data_list, target_list=self.startMsgArr):
                print("找到起始标识符数组")
                break  # 如果找到 target_list，退出循环
        # end_array = self.recProcessDataArr[-1]
        self.recProcessDataArr.pop()
        # 处理图像数据
        while self.recProcessDataArr:
            data_list = self.recProcessDataArr.popleft()  # 从左边弹出
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
        self.stopProcessingThread(0)

    # 接收数据处理
    def receiving_msg_processing(self, vci_can_obj):
        data_list = list(vci_can_obj.Data)
        with QMutexLocker(self.__Mutex):  # 确保线程安全
            # 检查是否需要处理的标志位
            self._processFlag = self.__recImageFlag or self.__recSqlTabNameFlag or self.__recCameraParamsFlag
            if self._processFlag:
                self.recProcessDataArr.append(data_list)
                if self.__recImageFlag:
                    self.__recPicCurrentSize += 8
                    self.fyCalPicProgressBar()
            else:
                self.recMsgSaveArr.append(data_list)
                self.__waitCondition.wakeAll()  # 唤醒等待的线程
                self.sig_messageReceived.emit(recList2Str(data_list))  # 发射信号，确保在主线程中
            # 检查处理线程是否需要启动
            if self._processFlag and not self.__processorThread:
                if self.__recImageFlag:
                    self.startThreadWithTimer(thread_type=0, timeout=20000)  # 开始处理线程
                else:
                    self.startThreadWithTimer(thread_type=0, timeout=10000)  # 开始处理线程

    # 计算进度条
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
            self.fyCheckSlaveStatus()
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
        time.sleep(0.05)
        rec_msg, rec_flag = self.fySendDataAndWait(message=self.StdData.arrSTATUS, timeout_ms=1000)
        if rec_flag:
            if rec_msg[2] == 48:
                self.__selfStatus = self.MachineStatus.Close
            elif rec_msg[2] == 49:
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
                self.__selfStatus = self.MachineStatus.MSG_END
            elif rec_msg[2] == 55:
                self.__selfStatus = self.MachineStatus.SQL_EDIT
            if rec_msg[5] == 48:
                self.__selfOperateMode = self.MachineOperate.Detect
            elif rec_msg[5] == 49:
                self.__selfOperateMode = self.MachineOperate.Compare
            elif rec_msg[5] == 50:
                self.__selfOperateMode = self.MachineOperate.Record
            print('当前下位机运行状态')
            print(self.__selfStatus)
            self.sig_statusUpdated.emit(str(self.__selfStatus), str(self.__selfOperateMode))
            time.sleep(0.05)
            return True
        else:
            print("Failed to receive message.")
            return False

    def fyCanSendData(self, send_data):
        self.change_send_data(send_data)
        self.can_send_msg()

    # 发送数据并等待接收
    def fySendDataAndWait(self, message, timeout_ms=5000):
        """发送数据并等待接收，带超时机制"""
        self.fyCanSendData(message)
        # 设置超时机制
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(self.onTimeout)
        timer.start(timeout_ms)

        with QMutexLocker(self.__Mutex):
            # 使用 QWaitCondition 和 QMutex 进行同步
            data_received = self.__waitCondition.wait(self.__Mutex, timeout_ms)

        # 停止定时器
        timer.stop()

        if not data_received:
            # 处理超时情况
            self.onTimeout()
            return None, False  # 返回 None 表示未接收到数据，False 表示操作失败

        # 返回接收到的数据和成功标志
        if self.recMsgSaveArr:
            data_rec = self.recMsgSaveArr[-1]
            return data_rec, True
        else:
            return None, False

    # 数据库数据信息处理
    def fySetSQLState(self, mission, byteName=None):
        if not self.fyCheckSlaveStatus():
            return False
        # 处理设备状态为 Ready
        if self.__selfStatus == self.MachineStatus.Ready:
            rec_msg, rec_flag = self.fySendDataAndWait(message=self.StdData.arrRE2SQL)
            if rec_msg:
                return self.fySetSQLState(mission, byteName)
            else:
                return False
        # 处理设备状态为 SQL
        elif self.__selfStatus == self.MachineStatus.SQL_EDIT:
            # 获取文件名
            if mission == 1:
                self.__recSqlTabNameFlag = True
                self.recProcessDataArr.clear()
                self.fyCanSendData(self.StdData.arrTNAM)
                return True
            elif mission == 2:
                # 切换文件
                self.fyCanSendData(self.StdData.arrTCHA)
                time.sleep(0.05)
                if byteName:
                    byteArr = strValue2CtypeArray(byteName)
                    self.fyCanSendData(byteArr)
                return True
            elif mission == 3:
                self.fyCanSendData(self.StdData.arrTDRO)
                time.sleep(0.05)
                if byteName:
                    byteArr = strValue2CtypeArray(byteName)
                    self.fyCanSendData(byteArr)
                return True
            elif mission == 4:
                self.fyCanSendData(self.StdData.arrTDRA)
                return True
            else:
                return False
        else:
            # 处理其他设备状态
            self.sig_errorDialog.emit('Machine Status Error.')
            self.tranStatus(self.MachineStatus.Ready)
            return self.fySetSQLState(mission, byteName)

    # 获取发送数据的标志位（用于参数设置）
    def getSendMsgByIndex(self, parameter_index, num_array):
        """根据参数索引获取发送消息"""
        if parameter_index == 0:
            return self.StdData.arrS2ROI1
        elif parameter_index == 4:
            return self.StdData.arrS2CAM1
        elif 8 <= parameter_index < 11:
            sendMsg = self.StdData.arrS2MODE
            sendMsg[5] = num_array[parameter_index - 8]
            return sendMsg
        elif parameter_index == 11:
            return self.StdData.arrS2NAME
        else:
            return None

    # parameter_array: 输入数据
    # parameter_index: 功能索引
    # 0<=ROI<4, 4<=CP<8, 8<=MODE<11, 11=FileName,12=LoadData
    def fySetCameraParameter(self, parameter_array, parameter_index):
        num_array = [0x00, 0x31, 0x32, 0x33, 0x34]
        # 检查设备状态
        if not self.fyCheckSlaveStatus():
            return False
        # 处理设备状态为 Ready
        if self.__selfStatus == self.MachineStatus.Ready:
            rec_msg, rec_flag = self.fySendDataAndWait(message=self.StdData.arrRE2ED)
            if rec_flag:
                time.sleep(0.05)
                return self.fySetCameraParameter(parameter_array, parameter_index)
            return True
        # 处理设备状态为 Edit
        elif self.__selfStatus == self.MachineStatus.Edit:

            if parameter_index == 12:
                # 下位机参数获取
                self.recProcessDataArr.clear()
                self.__recCameraParamsFlag = True
                self.fyCanSendData(self.StdData.arrGETPAR)
                return True
            sendMsg = self.getSendMsgByIndex(parameter_index, num_array)
            if parameter_index in [0, 4, 11]:
                # 切换标识符
                self.fyCanSendData(sendMsg)
                time.sleep(0.10)
            if parameter_index < 4:
                # ROI区域
                self.fySendDelayAndWaitACK(msg=parameter_array)
            elif 4 <= parameter_index < 8:
                # 相机参数
                self.fySendDelayAndWaitACK(msg=parameter_array)
            elif 8 <= parameter_index < 11:
                # 模式设置
                self.fySendDelayAndWaitACK(msg=sendMsg)
            elif parameter_index == 11:
                # 文件名字
                self.fySendDelayAndWaitACK(msg=parameter_array)
                self.sig_infoDialog.emit('文件名指令已发送')
        # 处理其他设备状态
        else:
            self.sig_errorDialog.emit('Machine Status Error.')
            self.tranStatus(self.MachineStatus.Ready)
            time.sleep(0.05)
            return self.fySetCameraParameter(parameter_array, parameter_index)

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
        self.fyTrans2Ready()
        if self.fyCheckSlaveStatus():
            if self.__selfStatus == self.MachineStatus.Ready:
                rec_msg, rec_flag = self.fySendDataAndWait(message=self.StdData.arrRE2AC)
                if compare_arr_ctypes_(input_arr=rec_msg, target_arr=self.StdData.arrPCO):
                    print('AC:下位机处于PCO')
                    self.fyCanSendData(self.StdData.arrACK)
                    time.sleep(0.05)
                    if self.fyCheckSlaveStatus():
                        if self.__selfStatus == self.MachineStatus.Activity:
                            print('下位机状态已经是Activity')
                            self.fyCanSendData(self.StdData.arrDetect)
                            self.detectFlag = True
                            time.sleep(0.05)
                            # 发送数据
                            self.startThreadWithTimer(thread_type=1, timeout=0)
                            # 接收数据
                            self.startThreadWithTimer(thread_type=0, timeout=0)
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

                self.fyCanSendData(self.StdData.arrDetect)
                return True
            else:
                self.sig_errorDialog.emit('Machine Status Error.')
                self.fyTrans2Ready()
                self.fyStartDetect()
        else:
            return False

    # 检测停止
    def fyStopDetect(self):
        self.stopProcessingThread(1)
        time.sleep(0.05)
        self.fyCanSendData(send_data=self.StdData.arrEND)
        time.sleep(0.05)

    # 向下位机发送接收图片请求
    def fyReceiveImage(self):
        self.fyTrans2Ready()
        if self.fyCheckSlaveStatus():
            if self.__selfStatus == self.MachineStatus.Ready:
                rec_msg, rec_flag = self.fySendDataAndWait(message=self.StdData.arrRE2PC)
                if compare_arr_ctypes_(input_arr=rec_msg, target_arr=self.StdData.arrPCO):
                    print('PIC:下位机处于PCO')
                    self.fyCanSendData(self.StdData.arrACK)
                    time.sleep(0.05)
                    if self.fyCheckSlaveStatus():
                        if self.__selfStatus == self.MachineStatus.PIC:
                            print('下位机状态已经是PIC')
                            self.recProcessDataArr.clear()
                            self.__recMsgFinishIndex = 0
                            len_msg, rec_flag = self.fySendDataAndWait(message=self.StdData.arrSTA)
                            self.__recPicAllSize = calNumberArray(len_msg)
                            self.__recPicCurrentSize = 0
                            self.sig_progressValue.emit(0)
                            self.sig_canStatus.emit(True, 6)
                            self.__calTime = time.time()
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
                time.sleep(0.05)
                self.fyCanSendData(self.StdData.arrSTA)
                self.recProcessDataArr.clear()
                self.__recImageFlag = True
                self.__recMsgFinishIndex = 0
                return True
            else:
                self.sig_errorDialog.emit('Machine Status Error.')
                return False
        else:
            return False

    # 状态转换
    def tranStatus(self, target_status):
        if not self.fyCheckSlaveStatus():
            return -2
        if target_status == self.__selfStatus:
            return 1
        status_map = {
            self.MachineStatus.Ready: {
                self.MachineStatus.PIC: self.StdData.arrRE2PC,
                self.MachineStatus.Edit: self.StdData.arrRE2ED,
                self.MachineStatus.Activity: self.StdData.arrRE2AC,
                self.MachineStatus.SQL_EDIT: self.StdData.arrRE2SQL,
            },
            self.MachineStatus.Edit: {
                self.MachineStatus.Ready: self.StdData.arrBA2RE,
            },
            self.MachineStatus.Activity: {
                self.MachineStatus.Ready: self.StdData.arrBA2RE,
            },
            self.MachineStatus.PIC: {
                self.MachineStatus.Ready: self.StdData.arrBA2RE,
            },
            self.MachineStatus.Open: {
                self.MachineStatus.Ready: self.StdData.arrOP2RE,
            },
            self.MachineStatus.MSG_END: {
                self.MachineStatus.Ready: self.StdData.arrEND,
            },
            self.MachineStatus.SQL_EDIT: {
                self.MachineStatus.Ready: self.StdData.arrBA2RE,
            }
        }
        target_data = status_map.get(self.__selfStatus, {}).get(target_status)
        if target_data:
            self.change_send_data(target_data)
            self.can_send_msg(send_id=self.__canID)
            return 1
        else:
            return -1

    # 转为准备状态
    def fyTrans2Ready(self):
        time.sleep(0.05)
        self.tranStatus(self.MachineStatus.Ready)
        time.sleep(0.05)


# 接收数据线程
class CanReceiverThread(FYCanThread):
    def run(self):
        while not self.isInterruptionRequested():
            if self.floating_yarn:
                self.floating_yarn.can_receive_msg_2()
                with QMutexLocker(self.mutex):
                    if self.floating_yarn.recMsgSaveArr:
                        self.wait_condition.wakeAll()  # 唤醒处理线程
            else:
                QThread.msleep(100)  # 延时，以避免占用过多 CPU 资源


# 接收数据处理线程
class CanProcessorThread(FYCanThread):
    def run(self):
        if self.floating_yarn is None:
            return  # 提前退出，如果floating_yarn为空
        while not self.isInterruptionRequested():
            with QMutexLocker(self.mutex):
                while not (
                        self.floating_yarn.recProcessDataArr) and not self.isInterruptionRequested():
                    self.wait_condition.wait(self.mutex)
                if self.isInterruptionRequested():
                    break
                if self.floating_yarn.recProcessDataArr:
                    data_list = self.floating_yarn.recProcessDataArr[-1]
                    if data_list:
                        if self.floating_yarn.detectFlag:
                            self.floating_yarn.detectResultProcess(data_list=data_list)
                        else:
                            self.floating_yarn.detectSpecificCharacters(
                                data_list=data_list,
                                target_list=self.floating_yarn.finishMsgArr
                            )


# 编织信息发送
class KnitSendThread(FYCanThread):
    def run(self):
        while not self.isInterruptionRequested():
            if self.floating_yarn is not None:
                send_data_array = self.floating_yarn.StdData.arrYARN
                sendRow = self.floating_yarn.knitRow
                row_array = numValue2CtypeArray(value_str=str(sendRow), length=5)
                for i in range(3, 8):
                    send_data_array[i] = row_array[i - 3]
                self.floating_yarn.fyCanSendData(send_data_array)
                time.sleep(0.05)
