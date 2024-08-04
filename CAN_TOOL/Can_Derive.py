# coding=UTF-8
import ctypes
from ctypes import *

# CAN设备类写法
from CAN_TOOL.CAN_MSG import VCI_CAN_OBJ


class Can_Derive:
    __VCI_USBCAN2 = 4
    __STATUS_OK = 1
    __STATUS_ERR = -1
    __STATUS_SEND_FINISH = 1
    __STATUS_RECEIVE_FINISH = 1
    __send_array = ctypes.c_ubyte * 8
    __receive_array = ctypes.c_ubyte * 8
    __reserved_array = ctypes.c_ubyte * 3

    def __init__(self, win_linux=0):
        # 导入库文件
        if win_linux == 1:
            self.__canDLL = ctypes.windll.LoadLibrary('./ControlCAN.dll')
        else:
            self.__canDLL = cdll.LoadLibrary('libcontrolcan.so')
        self.__reserved_data = self.__reserved_array(0, 0, 0)
        # 无意义，作为可替换类型
        self.__receive_data = self.__receive_array(0, 0, 0, 0, 0, 0, 0, 0)
        # 通过改变send_data来发送数据
        self.__send_data = self.__send_array(0, 0, 0, 0, 0, 0, 0, 0)
        self.__can_init_status = self.__STATUS_ERR
        self.__can_channel_0_status = self.__STATUS_ERR
        self.__can_channel_1_status = self.__STATUS_ERR
        self.__receive_status = self.__STATUS_ERR

        # 通信通道配置结构体

    # AccCode帧过滤验收码，AccMask帧过滤屏蔽码，Reserved保留，Filter方式，Timing0波特率定时器0，Timing1波特率定时器1，Mode模式（0正常，1只听，2自发自收）
    # 波特率    Timing0   Timing1
    # 500Kbps    0x00     0x1C
    # 1000 Kbps  0x00     0x14
    class VCI_INIT_CONFIG(ctypes.Structure):
        _fields_ = [("AccCode", ctypes.c_uint),
                    ("AccMask", ctypes.c_uint),
                    ("Reserved", ctypes.c_uint),
                    ("Filter", ctypes.c_ubyte),
                    ("Timing0", c_ubyte),
                    ("Timing1", c_ubyte),
                    ("Mode", c_ubyte)
                    ]

    # 发送帧结构体
    # ID:帧ID(靠右对齐)
    class VCI_CAN_OBJ(Structure):
        _fields_ = [("ID", c_uint),
                    ("TimeStamp", c_uint),
                    ("TimeFlag", c_ubyte),
                    ("SendType", c_ubyte),
                    ("RemoteFlag", c_ubyte),
                    ("ExternFlag", c_ubyte),
                    ("DataLen", c_ubyte),
                    ("Data", c_ubyte * 8),
                    ("Reserved", c_ubyte * 3)
                    ]

    class VCI_CAN_OBJ_ARRAY(Structure):
        _fields_ = [('SIZE', ctypes.c_uint16), ('STRUCT_ARRAY', ctypes.POINTER(VCI_CAN_OBJ))]

        def __init__(self, num_of_structs):
            # 这个括号不能少
            self.STRUCT_ARRAY = ctypes.cast((VCI_CAN_OBJ * num_of_structs)(), ctypes.POINTER(VCI_CAN_OBJ))  # 结构体数组
            self.SIZE = num_of_structs  # 结构体长度
            self.ADDR = self.STRUCT_ARRAY[0]  # 结构体数组地址  byref()转c地址

    def can_init(self):
        # VCI_OpenDevice打开设备
        self.__can_init_status = self.__canDLL.VCI_OpenDevice(self.__VCI_USBCAN2, 0, 0)
        if self.__can_init_status == self.__STATUS_OK:
            print('Can设备打开成功\r\n')
        if self.__can_init_status != self.__STATUS_OK:
            self.__can_init_status = self.__STATUS_ERR
            print('调用 VCI_OpenDevice出错\r\n')

    def can_channel_open(self, channel=0, baud=1000):
        if self.__can_init_status == self.__STATUS_ERR:
            print("Uninitialized!!")
            return self.__STATUS_ERR
        if baud == 500:
            vci_init_config = self.VCI_INIT_CONFIG(0x80000008, 0xFFFFFFFF, 0, 0, 0x00, 0x1C, 0)  # 波特率500k，正常模式
        elif baud == 1000:
            vci_init_config = self.VCI_INIT_CONFIG(0x80000008, 0xFFFFFFFF, 0, 0, 0x00, 0x14, 0)  # 波特率1M，正常模式
        else:
            vci_init_config = self.VCI_INIT_CONFIG(0x80000008, 0xFFFFFFFF, 0, 0, 0x04, 0x1C, 0)  # 波特率100K，正常模式
        if channel == 0:
            # 初始0通道
            # VCI_InitCAN此函数用以初始化指定的CAN通道。有多个CAN通道时，需要多次调用。
            can_0_init = self.__canDLL.VCI_InitCAN(self.__VCI_USBCAN2, 0, 0, byref(vci_init_config))
            if can_0_init == self.__STATUS_OK:
                print('CAN通道初始成功')
                print('波特率设置为')
                print(baud)
                print('\r\n')
            if can_0_init != self.__STATUS_OK:
                print('调用 VCI_InitCAN1出错\r\n')
                return self.__STATUS_ERR
            can_0_start = self.__canDLL.VCI_StartCAN(self.__VCI_USBCAN2, 0, 0)
            if can_0_start == self.__STATUS_OK:
                self.__can_channel_0_status = self.__STATUS_OK
                print('CAN通道打开成功\r\n')
                return self.__STATUS_OK
            if can_0_start != self.__STATUS_OK:
                self.__can_channel_0_status = self.__STATUS_ERR
                print('调用 VCI_StartCAN1出错\r\n')
                return self.__STATUS_ERR
        else:
            # 初始通道1
            can_1_init = self.__canDLL.VCI_InitCAN(self.__VCI_USBCAN2, 0, 1, byref(vci_init_config))
            if can_1_init == self.__STATUS_OK:
                print('调用 VCI_InitCAN2 成功\r\n')

            if can_1_init != self.__STATUS_OK:
                print('调用 VCI_InitCAN2 出错\r\n')
                return self.__STATUS_ERR
            can_1_start = self.__canDLL.VCI_StartCAN(self.__VCI_USBCAN2, 0, 1)
            if can_1_start == self.__STATUS_OK:
                self.__can_channel_1_status = self.__STATUS_OK
                print('调用 VCI_StartCAN2 成功\r\n')
                return self.__STATUS_OK
            if can_1_start != self.__STATUS_OK:
                self.__can_channel_1_status = self.__STATUS_ERR
                print('调用 VCI_StartCAN2 出错\r\n')
                return self.__STATUS_ERR

    def check_CAN_STATUS(self):
        if self.__can_init_status == self.__STATUS_ERR:
            return False
        if self.__can_channel_0_status == self.__STATUS_ERR:
            return False
        return True

    # 关闭CAN
    def can_close(self):
        self.__canDLL.VCI_CloseDevice(self.__VCI_USBCAN2, 0)
        self.__can_init_status = self.__STATUS_ERR
        print("关闭CAN设备")

    def can_send_msg(self, channel=0, send_id=0x01):
        if self.__can_init_status == self.__STATUS_ERR:
            print("Uninitialized!!")
            return self.__STATUS_ERR
        vci_can_obj = self.VCI_CAN_OBJ(send_id, 0, 0, 1, 0, 0, 8, self.__send_data, self.__reserved_data)
        if channel == 0:
            if self.__can_channel_0_status == self.__STATUS_ERR:
                print("Channel_0_Uninitialized")
                return self.__STATUS_ERR
            can_0_send_flag = self.__canDLL.VCI_Transmit(self.__VCI_USBCAN2, 0, 0, byref(vci_can_obj), 1)
            if can_0_send_flag == self.__STATUS_OK:
                print('CAN1通道发送成功\r\n')
                return self.__STATUS_SEND_FINISH
            if can_0_send_flag != self.__STATUS_OK:
                print('CAN1通道发送失败\r\n')
                return self.__STATUS_ERR
        else:
            if self.__can_channel_1_status == self.__STATUS_ERR:
                print("Channel_1_Uninitialized")
                return self.__STATUS_ERR
            can_1_send_flag = self.__canDLL.VCI_Transmit(self.__VCI_USBCAN2, 0, 1, byref(vci_can_obj), 1)
            if can_1_send_flag == self.__STATUS_OK:
                print('CAN2通道发送成功\r\n')
                return self.__STATUS_SEND_FINISH
            if can_1_send_flag != self.__STATUS_OK:
                print('CAN2通道发送失败\r\n')
                return self.__STATUS_ERR

    def can_receive_msg(self, channel=0, __STATUS_ERR=None):
        if self.__can_init_status == self.__STATUS_ERR:
            return self.__STATUS_ERR
        # 传入的是首地址
        rx_vci_can_obj = self.VCI_CAN_OBJ(0x33, 0, 0, 1, 0, 0, 8, self.__receive_data, self.__reserved_data)
        self.__receive_status = __STATUS_ERR
        if channel == 0:
            receive_flag = self.__canDLL.VCI_Receive(self.__VCI_USBCAN2, 0, 0, byref(rx_vci_can_obj), 2500, 0)
        else:
            receive_flag = self.__canDLL.VCI_Receive(self.__VCI_USBCAN2, 0, 1, byref(rx_vci_can_obj), 2500, 0)
        while receive_flag <= 0:
            if channel == 0:
                receive_flag = self.__canDLL.VCI_Receive(self.__VCI_USBCAN2, 0, 0, byref(rx_vci_can_obj), 2500, 0)
            else:
                receive_flag = self.__canDLL.VCI_Receive(self.__VCI_USBCAN2, 0, 1, byref(rx_vci_can_obj), 2500, 0)
        if receive_flag > 0:
            self.receiving_msg_processing(rx_vci_can_obj)
            return self.__STATUS_OK

    def can_receive_msg_2(self, channel=0):
        if self.__can_init_status == self.__STATUS_ERR:
            return self.__STATUS_ERR
        # 结构体数组
        rx_vci_can_obj = self.VCI_CAN_OBJ_ARRAY(2500)
        if channel == 0:
            receive_flag = self.__canDLL.VCI_Receive(self.__VCI_USBCAN2, 0, 0, byref(rx_vci_can_obj.ADDR), 2500, 0)
        else:
            receive_flag = self.__canDLL.VCI_Receive(self.__VCI_USBCAN2, 0, 1, byref(rx_vci_can_obj.ADDR), 2500, 0)
        while receive_flag <= 0:
            if channel == 0:
                receive_flag = self.__canDLL.VCI_Receive(self.__VCI_USBCAN2, 0, 0, byref(rx_vci_can_obj.ADDR), 2500, 0)
            else:
                receive_flag = self.__canDLL.VCI_Receive(self.__VCI_USBCAN2, 0, 1, byref(rx_vci_can_obj.ADDR), 2500, 0)
        if receive_flag > 0:
            for i in range(0, receive_flag):
                if rx_vci_can_obj.STRUCT_ARRAY[i].ID != 0:
                    self.receiving_msg_processing(rx_vci_can_obj.STRUCT_ARRAY[i])
                else:
                    return self.__STATUS_OK
            return self.__STATUS_OK

    def receiving_msg_processing(self, vci_can_obj):
        self.__receive_status = self.__STATUS_OK
        print("can_id:")
        print(vci_can_obj.ID)
        print("can_receive_data:")
        print(list(vci_can_obj.Data))
        print(" ")
        return vci_can_obj

    def change_send_data(self, data):
        self.__send_data = data

    def get_send_data(self):
        print(self.__send_data)
        return self.__send_data

    def getCanNowStatus(self):
        return self.__can_init_status


if __name__ == "__main__":
    can_derive = Can_Derive(win_linux=1)
    can_derive.can_init()
    can_derive.can_channel_open()
    for i in range(1, 4):
        # can_derive.can_receive_msg_2()
        can_derive.can_receive_msg()
    can_derive.can_close()
