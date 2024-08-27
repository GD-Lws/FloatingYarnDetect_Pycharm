# 浮沙检测上位机Demo -python

## 主要文件
| 文件                           |    功能    |
|:-----------------------------|:--------:|
| CAN_TOOL/CANMessageData.py   | 数据标识符存储类 |
| CAN_TOOL/Can_Derive.py       |  CAN驱动类  |
| candriver_layout.py          | 主界面布局文件  |
| SQLDialog.py                 | 数据库窗口布局文件 |
| FYCanThread.py               | QThread的封装类，用于生成处理线程 |
| FloatingYarn.py              | 通信交互类，用于实现通信和交互功能的实现 |
| main.py                      | 主窗口类，用于加载UI| 


## 主要实现功能
### CAN通信
- 主要实现CAN通信的开启关闭
- 波特率的切换
### 编织信息获取
- 当前编织文件的文件命
- 当前编织行数
- 当前编织速度
### 下位机图片获取
- 获取下位机当前图片 
### 检测模式切换
- 检测模式切换
- 下位机状态模式获取，Ready切换
### 下位机识别参数的设置读取
- 拍摄参数的设置读取(getCameraParams2EditText)
- 文件名（表名）的设置和读取(buttonSetFileName)
- 下位机数据库当前存储表名读取
- 下位机数据库删除所有表
- 下位机切换当前表
- 根据当前文件名新建表

## 下位机主要状态和检测模式
| serialStatus |    功能    |
|:-------------|:--------:|
| CLOSE        |  串口关闭状态  |
| OPEN         |  串口开启状态  |
| READY        |  检测准备状态  |
| ACTIVE       |  开始检测状态  |
| EDIT         |   参数编辑   |
| PIC          |   图片传输   |
| MSG_END      | 图片数据传输结束 | 
| SQL_EDIT     |  数据库编辑类  | 

| operateMode |    功能    |
|:-------------|:--------:|
| Detect        |  常规检测模式  |
| Compare         |  比较检测模式  |
| Record        | 样本数据采集模式 |


## 数据库主要功能函数
1. loadSqlData
2. toggleSqlData
3. addItems2Table 
4. dropSqlData 
5. dropSqlAllData 
6. getSelectedRadioButtonFromTable
7. fySetSQLState

## 相机参数主要功能函数
1. fySetCameraParameter
2. cameraParameterSet
3. roiParameterSet
4. getCameraParams2EditText


