# coding=UTF-8
from ctypes import *
# 结构体数组类
import ctypes


# Author: Lws
# Time: 2022/5/25
# Can设备函数写法

VCI_USBCAN2 = 4
STATUS_OK = 1
STATUS_ERR = -1
STATUS_SEND_FINISH = 2
STATUS_RECEIVE_FINISH = 2
# 用于判断CAN是否初始化
can_init_status = STATUS_ERR
can_channel_0_status = STATUS_ERR
can_channel_1_status = STATUS_ERR
WIN_OR_LINUX = 1
CanDLLName = './ControlCAN.dll'  # 把DLL放到对应的目录下
if WIN_OR_LINUX == 1:
    canDLL = windll.LoadLibrary('./ControlCAN.dll')
else:
    canDLL = cdll.LoadLibrary('libcontrolcan.so')
# 发送用
send_array = c_ubyte * 8
reserved_array = c_ubyte * 3
reserved_data = reserved_array(0, 0, 0)
send_data = send_array(0, 0, 0, 0, 0, 0, 0, 0)


# 通信通道配置结构体
# AccCode帧过滤验收码，AccMask帧过滤屏蔽码，Reserved保留，Filter方式，Timing0波特率定时器0，Timing1波特率定时器1，Mode模式（0正常，1只听，2自发自收）
# 波特率    Timing0   Timing1
# 500Kbps    0x00     0x1C
# 1000 Kbps  0x00     0x14
class VCI_INIT_CONFIG(Structure):
    _fields_ = [("AccCode", c_uint),
                ("AccMask", c_uint),
                ("Reserved", c_uint),
                ("Filter", c_ubyte),
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


def can_init():
    # VCI_OpenDevice打开设备
    global can_init_status
    can_init_status = canDLL.VCI_OpenDevice(VCI_USBCAN2, 0, 0)
    if can_init_status == STATUS_OK:
        print('调用 VCI_OpenDevice成功\r\n')
    if can_init_status != STATUS_OK:
        can_init_status = STATUS_ERR
        print('调用 VCI_OpenDevice出错\r\n')


def can_channel_open(channel=0, baud=1000):
    global can_channel_0_status, can_channel_1_status
    if can_init_status == STATUS_ERR:
        print("Uninitialized!!")
        return
    if baud == 500:
        vci_init_config = VCI_INIT_CONFIG(0x80000008, 0xFFFFFFFF, 0, 0, 0x00, 0x1C, 0)  # 波特率500k，正常模式
    elif baud == 1000:
        vci_init_config = VCI_INIT_CONFIG(0x80000008, 0xFFFFFFFF, 0, 0, 0x00, 0x14, 0)  # 波特率1M，正常模式
    else:
        vci_init_config = VCI_INIT_CONFIG(0x80000008, 0xFFFFFFFF, 0, 0, 0x04, 0x1C, 0)  # 波特率100K，正常模式
    if channel == 0:
        # 初始0通道
        # VCI_InitCAN此函数用以初始化指定的CAN通道。有多个CAN通道时，需要多次调用。
        can_0_init = canDLL.VCI_InitCAN(VCI_USBCAN2, 0, 0, byref(vci_init_config))
        if can_0_init == STATUS_OK:
            print('调用 VCI_InitCAN1成功\r\n')
        if can_0_init != STATUS_OK:
            print('调用 VCI_InitCAN1出错\r\n')
        can_0_start = canDLL.VCI_StartCAN(VCI_USBCAN2, 0, 0)
        if can_0_start == STATUS_OK:
            can_channel_0_status = STATUS_OK
            print('调用 VCI_StartCAN1成功\r\n')
        if can_0_start != STATUS_OK:
            can_channel_0_status = STATUS_ERR
            print('调用 VCI_StartCAN1出错\r\n')
    else:
        # 初始1通道
        can_1_init = canDLL.VCI_InitCAN(VCI_USBCAN2, 0, 1, byref(vci_init_config))
        if can_1_init == STATUS_OK:
            print('调用 VCI_InitCAN2 成功\r\n')
        if can_1_init != STATUS_OK:
            print('调用 VCI_InitCAN2 出错\r\n')
        can_1_start = canDLL.VCI_StartCAN(VCI_USBCAN2, 0, 1)
        if can_1_start == STATUS_OK:
            can_channel_1_status = STATUS_OK
            print('调用 VCI_StartCAN2 成功\r\n')
        if can_1_start != STATUS_OK:
            can_channel_1_status = STATUS_ERR
            print('调用 VCI_StartCAN2 出错\r\n')


# 关闭CAN
def can_close():
    global can_init_status
    canDLL.VCI_CloseDevice(VCI_USBCAN2, 0)
    can_init_status = STATUS_ERR


def can_send_msg(channel=0, send_id=0x01, send_data=[]):
    if can_init_status == STATUS_ERR:
        print("Uninitialized!!")
        return STATUS_ERR
    vci_can_obj = VCI_CAN_OBJ(send_id, 0, 0, 1, 0, 0, 8, send_data, reserved_data)
    if channel == 0:
        if can_channel_0_status == STATUS_ERR:
            print("Channel_0_Uninitialized")
            return STATUS_ERR
        can_0_send_flag = canDLL.VCI_Transmit(VCI_USBCAN2, 0, 0, byref(vci_can_obj), 1)
        if can_0_send_flag == STATUS_OK:
            print('CAN1通道发送成功\r\n')
            return STATUS_SEND_FINISH
        if can_0_send_flag != STATUS_OK:
            print('CAN1通道发送失败\r\n')
            return STATUS_ERR
    else:
        if can_channel_1_status == STATUS_ERR:
            print("Channel_1_Uninitialized")
            return STATUS_ERR
        can_1_send_flag = canDLL.VCI_Transmit(VCI_USBCAN2, 0, 1, byref(vci_can_obj), 1)
        if can_1_send_flag == STATUS_OK:
            print('CAN2通道发送成功\r\n')
            return STATUS_SEND_FINISH
        if can_1_send_flag != STATUS_OK:
            print('CAN2通道发送失败\r\n')
            return STATUS_ERR


def can_receive_msg_2(channel=0):
    if can_init_status == STATUS_ERR:
        return STATUS_ERR
    # 结构体数组
    rx_vci_can_obj = VCI_CAN_OBJ_ARRAY(2500)
    if channel == 0:
        receive_flag = canDLL.VCI_Receive(VCI_USBCAN2, 0, 0, byref(rx_vci_can_obj.ADDR), 2500, 0)
    else:
        receive_flag = canDLL.VCI_Receive(VCI_USBCAN2, 0, 1, byref(rx_vci_can_obj.ADDR), 2500, 0)
    while receive_flag <= 0:
        if channel == 0:
            receive_flag = canDLL.VCI_Receive(VCI_USBCAN2, 0, 0, byref(rx_vci_can_obj.ADDR), 2500, 0)
        else:
            receive_flag = canDLL.VCI_Receive(VCI_USBCAN2, 0, 1, byref(rx_vci_can_obj.ADDR), 2500, 0)
    if receive_flag > 0:
        print('CAN2通道接收成功\r\n')
        print(rx_vci_can_obj.STRUCT_ARRAY[0].ID)
        print(list(rx_vci_can_obj.STRUCT_ARRAY[0].Data))
        print(rx_vci_can_obj.STRUCT_ARRAY[1].ID)
        print(list(rx_vci_can_obj.STRUCT_ARRAY[1].Data))
        print(rx_vci_can_obj.STRUCT_ARRAY[2].ID)
        return STATUS_RECEIVE_FINISH


def can_receive_msg(channel=0):
    if can_init_status == STATUS_ERR:
        return STATUS_ERR
    # 传入的是首地址
    rx_vci_can_obj = VCI_CAN_OBJ(0x33, 0, 0, 1, 0, 0, 8, send_data, reserved_data)
    if channel == 0:
        receive_flag = canDLL.VCI_Receive(VCI_USBCAN2, 0, 0, byref(rx_vci_can_obj), 2500, 0)
    else:
        receive_flag = canDLL.VCI_Receive(VCI_USBCAN2, 0, 1, byref(rx_vci_can_obj), 2500, 0)
    while receive_flag <= 0:
        if channel == 0:
            receive_flag = canDLL.VCI_Receive(VCI_USBCAN2, 0, 0, byref(rx_vci_can_obj), 2500, 0)
        else:
            receive_flag = canDLL.VCI_Receive(VCI_USBCAN2, 0, 1, byref(rx_vci_can_obj), 2500, 0)
    if receive_flag > 0:
        print('CAN2通道接收成功\r\n')
        print(rx_vci_can_obj.ID)
        print(list(rx_vci_can_obj.Data))
        return STATUS_RECEIVE_FINISH



