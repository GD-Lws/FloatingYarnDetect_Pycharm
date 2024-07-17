import base64
from PIL import Image
import io


def decode_and_display_image(file_path):
    try:
        # 读取文档内容
        with open(file_path, 'r') as file:
            encoded_data = file.read()
        items = encoded_data.split('ChunkID:')
        result_string = ""
        for item in items[1:]:
            lines = item.splitlines()
            # package_id = lines[0]
            data_lines = lines[1:]
            data_string = '\n'.join(data_lines)
            result_string += data_string
            # print(data_string)
        print(result_string)
        # 解码Base64数据
        decoded_data = base64.b64decode(result_string)

        # 创建BytesIO对象以便PIL处理
        image_stream = io.BytesIO(decoded_data)

        # 打开图像
        image = Image.open(image_stream)

        # 显示图像
        image.show()

    except Exception as e:
        print(f"Error decoding or displaying image: {e}")


def main():
    file_path = 'rec_txt/recv_2024-07-05_14-13-00.txt'  # 你的文档路径
    decode_and_display_image(file_path)


if __name__ == "__main__":
    main()
