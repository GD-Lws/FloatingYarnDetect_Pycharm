import threading
import time
from collections import deque
from ctypes import byref
from enum import Enum

from CANMessageData import CANMessageData
from Can_Derive import Can_Derive


class FloatingYarn(Can_Derive):
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

    def __init__(self, win_linux=1, send_id=0x141, max_messages=10000):
        super().__init__(win_linux=win_linux)
        self.__selfState = self.MachineStatus.Close
        self.StdData = CANMessageData()
        self.can_init()
        self.can_channel_open()
        self.received_messages = deque(maxlen=max_messages)  # 使用 deque 限制消息数量
        self.receive_thread = threading.Thread(target=self.receive_loop, args=(0,))
        self.receive_thread.daemon = True  # 设置为守护线程
        self.receive_thread.start()
        self.lock = threading.Lock()  # 添加锁
        self.message_event = threading.Event()
        self.canID = 0x141
        self.__recImage_arr = []
        self.__recImage_Flag = False
        self.__recMsgFinishIndex = 0
        self.output_path = 'rec_txt/output_image.jpg'

    def receive_image(self):
        if self.check_status():
            if self.__selfState == self.MachineStatus.Ready:
                rec_flag, rec_msg = self.send_and_wait_for_response(self.StdData.arrRE2PC, ack_flag=True)
                if rec_msg == self.StdData.arrPCO:
                    self.fy_sendData(self.StdData.arrSTA)

                elif rec_msg == self.StdData.arrPCC:
                    pass
            elif self.__selfState == self.MachineStatus.PIC:

                return False
        else:
            return False

    def save_bytes_as_image(self):
        with open(self.output_path, 'wb') as image_file:
            image_file.write(self.__recImage_arr)

    def receiving_msg_processing(self, vci_can_obj):
        data_list = list(vci_can_obj.Data)
        with self.lock:  # 访问 deque 时加锁
            self.received_messages.append(data_list)
            if self.__recImage_Flag:
                self.__recImage_arr.append(data_list)
                self.detect_SpecificCharacters(data_list)
        self.message_event.set()  # 触发事件
        return vci_can_obj

    def detect_SpecificCharacters(self, data_list):
        if self.__recMsgFinishIndex == 8:
            self.__recMsgFinishIndex = 0
            self.__recImage_Flag = False
            return
        for data in data_list:
            if data == self.StdData.arrMSG_FINISH[self.__recMsgFinishIndex]:
                self.__recMsgFinishIndex = self.__recMsgFinishIndex + 1
            else:
                self.__recMsgFinishIndex = 0

    def start_receiving(self, channel=0):
        # 启动接收线程（如果还没启动的话）
        if not self.receive_thread.is_alive():
            self.receive_thread = threading.Thread(target=self.receive_loop, args=(channel,))
            self.receive_thread.daemon = True
            self.receive_thread.start()

    def receive_loop(self, channel):
        while True:
            # 持续接收消息
            self.can_receive_msg(channel)

    def get_received_messages(self):
        # 返回接收到的消息列表
        messages = list(self.received_messages)
        return messages

    def get_latest_message(self):
        with self.lock:  # 访问 deque 时加锁
            if self.received_messages:
                # 返回最新的一条消息
                return self.received_messages[-1]
            return None

    def fy_sendData(self, sendData):
        self.change_send_data(sendData)
        self.can_send_msg(send_id=self.canID)

    # ack_flag 接收后是否响应
    def send_and_wait_for_response(self, send_data, send_id=0x141, timeout=5, ack_flag=False):
        self.fy_sendData(send_data)
        # 清除事件状态
        self.message_event.clear()
        # 等待事件触发或超时
        if not self.message_event.wait(timeout=timeout):
            # 超时
            print("Timeout: No message received within the time limit.")
            return False, None

        # 获取最新的消息
        latest_message = self.get_latest_message()
        if latest_message is not None:
            if ack_flag:
                self.fy_sendData(self.StdData.arrACK)
            return True, latest_message
        return False, None

    def check_status(self, timeout=5):
        rec_flag, rec_msg = self.send_and_wait_for_response(self.StdData.arrSTATUS, timeout=timeout)
        if rec_flag:
            if rec_msg[2] == 49:
                self.__selfState = self.MachineStatus.Open
            elif rec_msg[2] == 50:
                self.__selfState = self.MachineStatus.Ready
            elif rec_msg[2] == 51:
                self.__selfState = self.MachineStatus.Activate
            elif rec_msg[2] == 52:
                self.__selfState = self.MachineStatus.Edit
            elif rec_msg[2] == 53:
                self.__selfState = self.MachineStatus.PIC
            elif rec_msg[2] == 54:
                self.__selfState = self.MachineStatus.PIC

            return True
        else:
            print("Failed to receive message.")
            return False

    def trans_status(self, target_status):
        if self.check_status():
            if self.__selfState == self.MachineStatus.Ready:
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
            elif self.__selfState == self.MachineStatus.Edit:
                if target_status == self.MachineStatus.Ready:
                    self.change_send_data(self.StdData.arrBA2RE)
                else:
                    return -1
            elif self.__selfState == self.MachineStatus.Activate:
                if target_status == self.MachineStatus.Ready:
                    self.change_send_data(self.StdData.arrBA2RE)
                else:
                    return -1
            elif self.__selfState == self.MachineStatus.PIC:
                if target_status == self.MachineStatus.Ready:
                    self.change_send_data(self.StdData.arrBA2RE)
                else:
                    return -1
            elif self.__selfState == self.MachineStatus.Open:
                if target_status == self.MachineStatus.Ready:
                    self.change_send_data(self.StdData.arrOP2RE)
                else:
                    return -1
            self.can_send_msg(send_id=self.canID)
            return 1
        else:
            return -2


if __name__ == "__main__":
    can_device = FloatingYarn()

    # 启动接收线程
    can_device.start_receiving()

    # 发送测试消息
    can_device.check_status()

    # 主线程可以做其他事情
    # while True:
    #     # pass
    #     can_device.check_status()
    # 获取并处理接收到的消息
    # messages = can_device.get_received_messages()
    # if messages:
    #     print("Processing messages:", messages)
    # time.sleep(1)  # 主线程的其他操作
