# import threading
# import time
# from collections import deque
# from enum import Enum
#
# from PyQt5.QtCore import QObject, QThread, pyqtSignal
# from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject
#
# from CANMessageData import CANMessageData
# from Can_Derive import Can_Derive
#
#
# def compare_arr_ctypes_(input_arr, target_arr):
#     arrTarget_int = [int(x) for x in input_arr]
#     for i in range(8):
#         if arrTarget_int[i] != input_arr[i]:
#             return False
#     return True
#
#
# class ReceiveThread(QThread):
#     data_received = pyqtSignal(list)  # 定义信号
#
#     def __init__(self, floating_yarn, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.floating_yarn = floating_yarn
#
#     def run(self):
#         # 模拟数据接收
#         for i in range(5):
#             self.floating_yarn.receiving_msg_processing()
#             self.sleep(1)  # 模拟延迟
#
#
# class FloatingYarn(Can_Derive, QObject):
#     data_received = pyqtSignal(list)
#
#     class MachineStatus(Enum):
#         Close = 0
#         Open = 1
#         Ready = 2
#         Activate = 3
#         Edit = 4
#         PIC = 5
#
#     class MachineOperate(Enum):
#         Detect = 0
#         Compare = 1
#         Record = 2
#
    def __init__(self, win_linux=1, send_id=0x141, max_messages=10000):
        super().__init__()  # Initialize QObject
        Can_Derive.__init__(self, win_linux=win_linux)
        self.__selfStatus = self.MachineStatus.Close
        self.__selfOperateMode = self.MachineOperate.Detect
        self.StdData = CANMessageData()
        self.can_init()
        self.can_channel_open()
        self.received_messages = deque(maxlen=max_messages)
        self.receive_thread = ReceiveThread(self)
        self.receive_thread.data_received.connect(self.on_data_received)
        self.receive_thread.start()
        self.lock = threading.Lock()
        self.canID = 0x141
        self.__recImage_arr = []
        self.__recImage_Flag = False
        self.__recMsgFinishIndex = 0
        self.output_path = 'rec_txt/output_image.jpg'

#     def fy_receive_image(self):
#         if self.check_status():
#             if self.__selfStatus == self.MachineStatus.Ready:
#                 rec_flag, rec_msg = self.send_and_wait_for_response(self.StdData.arrRE2PC, ack_flag=True)
#                 if compare_arr_ctypes_(input_arr=rec_msg, target_arr=self.StdData.arrPCO):
#                     self.fy_sendData(self.StdData.arrSTA)
#                     return True
#                 elif compare_arr_ctypes_(input_arr=rec_msg, target_arr=self.StdData.arrPCC):
#                     self.fy_receive_image()
#                     return True
#             elif self.__selfStatus == self.MachineStatus.PIC:
#                 self.fy_sendData(self.StdData.arrSTA)
#                 return True
#         else:
#             return False
#
#     def on_data_received(self, data_list):
#         # Slot to handle received data
#         print("Data received:", data_list)
#
#     def receiving_msg_processing(self, vci_can_obj):
#         data_list = list(vci_can_obj.Data)
#         self.received_messages.append(data_list)
#         self.data_received.emit(data_list)  # 发送信号
#
#     def detect_SpecificCharacters(self, data_list):
#         if self.__recMsgFinishIndex == 8:
#             self.__recMsgFinishIndex = 0
#             self.__recImage_Flag = False
#             return
#         for data in data_list:
#             if data == self.StdData.arrMSG_FINISH[self.__recMsgFinishIndex]:
#                 self.__recMsgFinishIndex = self.__recMsgFinishIndex + 1
#             else:
#                 self.__recMsgFinishIndex = 0
#
#     def start_receiving(self, channel=0):
#         # 启动接收线程（如果还没启动的话）
#         if not self.receive_thread.is_alive():
#             self.receive_thread = threading.Thread(target=self.receive_loop, args=(channel,))
#             self.receive_thread.daemon = True
#             self.receive_thread.start()
#
#     def receive_loop(self, channel):
#         while True:
#             # 持续接收消息
#             self.can_receive_msg(channel)
#
#     def get_received_messages(self):
#         # 返回接收到的消息列表
#         messages = list(self.received_messages)
#         return messages
#
#     def get_latest_message(self):
#         with self.lock:  # 访问 deque 时加锁
#             if self.received_messages:
#                 # 返回最新的一条消息
#                 return self.received_messages[-1]
#             return None
#
#     def fy_sendData(self, sendData):
#         self.change_send_data(sendData)
#         self.can_send_msg(send_id=self.canID)
#
#     # ack_flag 接收后是否响应
#     def send_and_wait_for_response(self, send_data, send_id=0x141, timeout=5, ack_flag=False):
#         self.fy_sendData(send_data)
#         # 清除事件状态
#         self.message_event.clear()
#         # 等待事件触发或超时
#         if not self.message_event.wait(timeout=timeout):
#             # 超时
#             print("Timeout: No message received within the time limit.")
#             return False, None
#
#         # 获取最新的消息
#         latest_message = self.get_latest_message()
#         if latest_message is not None:
#             if ack_flag:
#                 self.fy_sendData(self.StdData.arrACK)
#             return True, latest_message
#         return False, None
#
    # def check_status(self, timeout=5):
    #     rec_flag, rec_msg = self.send_and_wait_for_response(self.StdData.arrSTATUS, timeout=timeout)
    #     if rec_flag:
    #         if rec_msg[2] == 49:
    #             self.__selfStatus = self.MachineStatus.Open
    #         elif rec_msg[2] == 50:
    #             self.__selfStatus = self.MachineStatus.Ready
    #         elif rec_msg[2] == 51:
    #             self.__selfStatus = self.MachineStatus.Activate
    #         elif rec_msg[2] == 52:
    #             self.__selfStatus = self.MachineStatus.Edit
    #         elif rec_msg[2] == 53:
    #             self.__selfStatus = self.MachineStatus.PIC
    #         elif rec_msg[2] == 54:
    #             self.__selfStatus = self.MachineStatus.PIC
    #         if rec_msg[5] == 49:
    #             self.__selfOperateMode = self.MachineOperate.Detect
    #         elif rec_msg[5] == 50:
    #             self.__selfOperateMode = self.MachineOperate.Compare
    #         elif rec_msg == 51:
    #             self.__selfOperateMode = self.MachineOperate.Record
    #     else:
    #         print("Failed to receive message.")
    #         return False
#
#     def trans_status(self, target_status):
#         if self.check_status():
#             if self.__selfStatus == self.MachineStatus.Ready:
#                 if target_status == self.MachineStatus.Ready:
#                     return 1
#                 elif target_status == self.MachineStatus.PIC:
#                     self.change_send_data(self.StdData.arrRE2PC)
#                 elif target_status == self.MachineStatus.Edit:
#                     self.change_send_data(self.StdData.arrRE2ED)
#                 elif target_status == self.MachineStatus.Activate:
#                     self.change_send_data(self.StdData.arrRE2AC)
#                 else:
#                     return -1
#             elif self.__selfStatus == self.MachineStatus.Edit:
#                 if target_status == self.MachineStatus.Ready:
#                     self.change_send_data(self.StdData.arrBA2RE)
#                 else:
#                     return -1
#             elif self.__selfStatus == self.MachineStatus.Activate:
#                 if target_status == self.MachineStatus.Ready:
#                     self.change_send_data(self.StdData.arrBA2RE)
#                 else:
#                     return -1
#             elif self.__selfStatus == self.MachineStatus.PIC:
#                 if target_status == self.MachineStatus.Ready:
#                     self.change_send_data(self.StdData.arrBA2RE)
#                 else:
#                     return -1
#             elif self.__selfStatus == self.MachineStatus.Open:
#                 if target_status == self.MachineStatus.Ready:
#                     self.change_send_data(self.StdData.arrOP2RE)
#                 else:
#                     return -1
#             self.can_send_msg(send_id=self.canID)
#             return 1
#         else:
#             return -2
