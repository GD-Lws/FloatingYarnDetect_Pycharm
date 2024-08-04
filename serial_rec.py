import serial
import serial.tools.list_ports
import time
from PIL import Image


def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]


def receive_image_from_serial(port, baudrate=115200, timeout=1, max_wait_time=10):
    # 设置串口
    ser = serial.Serial(port, baudrate, timeout=timeout)

    # 记录开始接收数据的时间
    start_time = time.time()

    # 读取串口数据
    jpeg_data = bytearray()
    while True:
        if ser.in_waiting:
            data = ser.read(ser.in_waiting)
            jpeg_data.extend(data)
            if b"END" in jpeg_data:
                jpeg_data = jpeg_data[:-3]  # 去除 "END" 标志
                break

    # 记录完成接收数据的时间
    end_time = time.time()

    # 计算接收数据所用的时间
    elapsed_time = end_time - start_time
    print(f"Data received in {elapsed_time:.2f} seconds")

    # 将接收到的字节数组保存为JPEG文件
    with open("Picture/received_image.jpg", "wb") as f:
        f.write(jpeg_data)

    # 打开并显示图像
    img = Image.open("Picture/received_image.jpg")
    img.show()



def main():
    # 列出所有可用的串口
    available_ports = list_serial_ports()
    if not available_ports:
        print("No serial ports found.")
        return

    print("Available serial ports:")
    for i, port in enumerate(available_ports):
        print(f"{i}: {port}")

    # 让用户选择串口
    try:
        port_index = int(input("Select the serial port index: "))
        selected_port = available_ports[port_index]
        print(f"Selected port: {selected_port}")

        # 接收并处理图像数据
        receive_image_from_serial(selected_port)
    except (ValueError, IndexError):
        print("Invalid selection. Please restart the program and select a valid index.")


if __name__ == "__main__":
    main()
