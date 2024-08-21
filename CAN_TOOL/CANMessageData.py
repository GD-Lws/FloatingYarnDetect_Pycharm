import ctypes
from dataclasses import dataclass


class c_ubyte_Array_8(ctypes.c_ubyte * 8):
    pass


@dataclass
class CANMessageData:
    arrRE2SQL: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x52, 0x45, 0x32, 0x53, 0x51, 0x4C, 0x0d, 0x0a])
    # 表已新建
    arrTABEXIT: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x54, 0x45, 0x58, 0x49, 0x54, 0x0d, 0x0a, 0x00])
    # 表新建
    arrTABCREAT: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x54, 0x43, 0x52, 0x45, 0x0d, 0x0a, 0x00, 0x00])
    # 删除表
    arrTDRO: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x54, 0x44, 0x52, 0x4F, 0x0d, 0x0a, 0x00, 0x00])
    # 获取所有表名
    arrTNAM: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x54, 0x4E, 0x41, 0x4D, 0x0d, 0x0a, 0x00, 0x00])
    # 换表
    arrTCHA: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x54, 0x43, 0x48, 0x41, 0x3A, 0x31, 0x00, 0x00])
    arrTDRA: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x54, 0x44, 0x52, 0x41, 0x0d, 0x0a, 0x00, 0x00])
    arrGETPAR: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x47, 0x45, 0x54, 0x50, 0x41, 0x52, 0x0d, 0x0a])

    arrHeartBeat: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x63, 0x69, 0x78, 0x69, 0x6e, 0x67, 0x0d, 0x0a])
    arrDetect: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x44, 0x45, 0x54, 0x45, 0x43, 0x54, 0x0d, 0x0a])
    arrRE2PC: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x52, 0x45, 0x32, 0x50, 0x43, 0x0d, 0x0a, 0x00])
    arrRE2ED: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x52, 0x45, 0x32, 0x45, 0x44, 0x0d, 0x0a, 0x00])
    arrRE2AC: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x52, 0x45, 0x32, 0x41, 0x43, 0x0d, 0x0a, 0x00])
    arrBA2RE: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x42, 0x41, 0x32, 0x52, 0x45, 0x0d, 0x0a, 0x00])
    arrOP2RE: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x4F, 0x50, 0x32, 0x52, 0x45, 0x0d, 0x0a, 0x00])
    arrSTATUS: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x53, 0x54, 0x41, 0x54, 0x55, 0x53, 0x0d, 0x0a])

    arrSTA: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x53, 0x54, 0x41, 0x0d, 0x0a, 0x00, 0x00, 0x00])
    arrACK: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x41, 0x43, 0x4B, 0x0d, 0x0a, 0x00, 0x00, 0x00])
    arrEND: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x45, 0x4E, 0x44, 0x0d, 0x0a, 0x00, 0x00, 0x00])
    arrMSG_START: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07])
    arrMSG_FINISH: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F])

    arrPCO: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x50, 0x43, 0x4F, 0x0d, 0x0a, 0x00, 0x00, 0x00])
    arrPCC: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x50, 0x43, 0x43, 0x0d, 0x0a, 0x00, 0x00, 0x00])

    arrS2ROI1: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x53, 0x32, 0x52, 0x4F, 0x49, 0x31, 0x0d, 0x0a])
    arrS2CAM1: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x53, 0x32, 0x43, 0x41, 0x4D, 0x31, 0x0d, 0x0a])
    arrS2CAM2: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x53, 0x32, 0x43, 0x41, 0x4D, 0x32, 0x0d, 0x0a])
    arrS2CAM3: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x53, 0x32, 0x43, 0x41, 0x4D, 0x33, 0x0d, 0x0a])
    arrS2CAM4: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x53, 0x32, 0x43, 0x41, 0x4D, 0x34, 0x0d, 0x0a])
    arrS2MODE: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x4D, 0x4F, 0x44, 0x45, 0x3A, 0x31, 0x0d, 0x0a])
    arrS2NAME: c_ubyte_Array_8 = c_ubyte_Array_8(*[0x53, 0x32, 0x4E, 0x61, 0x6D, 0x65, 0x0d, 0x0a])
