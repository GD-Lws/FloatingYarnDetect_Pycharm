import pandas as pd


# 定义 ASCII 解析函数
def ascii_parse(hex_str):
    hex_list = hex_str.strip().split()  # 去除空格并分割字符串
    bytes_list = [int(x, 16) for x in hex_list[1:]]  # 转换为整数列表
    ascii_str = ''.join(chr(byte) for byte in bytes_list)  # 转换为 ASCII 字符串
    return ascii_str


def main():
    # 读取 Excel 文件
    file_path = 'rec_can/1658.csv'  # 替换为实际的文件路径

    # 使用 pandas 读取 Excel 文件
    df = pd.read_csv(file_path)

    # 假设要解析的列名为 'Data'，可以根据实际情况修改
    column_name = r'Data'

    # 对 'Data' 列应用 ASCII 解析函数
    df['ASCII_Data'] = df[column_name].apply(ascii_parse)

    # 写入到 txt 文件
    output_file = 'output.txt'

    with open(output_file, 'w') as f:
        for index, row in df.iterrows():
            f.write(f"{row['ASCII_Data']}")

    print(f"解析结果已写入到文件: {output_file}")


if __name__ == "__main__":
    main()
