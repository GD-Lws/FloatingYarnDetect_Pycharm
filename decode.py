import pandas as pd
import binascii
import re


# 定义 HEX 解析函数
def hex_parse(hex_str):
    hex_list = hex_str.strip().split()  # 去除空格并分割字符串
    return hex_list


def clean_hex_data(hex_list):
    # 过滤掉非十六进制字符
    cleaned_hex = ''.join(hex_list)
    if re.fullmatch(r'[0-9A-Fa-f]+', cleaned_hex):
        return cleaned_hex
    else:
        raise ValueError("Invalid HEX data found")


def hex_to_bytes(hex_data):
    return binascii.unhexlify(hex_data)


def save_bytes_as_image(byte_data, output_path):
    with open(output_path, 'wb') as image_file:
        image_file.write(byte_data)


def main():
    # 读取 CSV 文件
    file_path = 'rec_can/1656.csv'  # 替换为实际的文件路径

    # 使用 pandas 读取 CSV 文件
    df = pd.read_csv(file_path)

    # 假设要解析的列名为 'Data'
    column_name = 'Data'

    # 对 'Data' 列应用 HEX 解析函数
    df['HEX_Data'] = df[column_name].apply(hex_parse)

    # 将 HEX 数据列表转换为单一的字符串
    hex_data = ''.join(df['HEX_Data'].apply(lambda x: ''.join(x)))

    # 清理 HEX 数据
    try:
        cleaned_hex_data = clean_hex_data(df['HEX_Data'].explode())
        byte_data = hex_to_bytes(cleaned_hex_data)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # 保存字节数据为图像文件
    output_image_path = 'output_image_2.jpg'
    save_bytes_as_image(byte_data, output_image_path)

    print(f'Image saved to {output_image_path}')


if __name__ == "__main__":
    main()
