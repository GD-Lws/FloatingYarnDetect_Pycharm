import binascii


def read_hex_from_file(file_path):
    with open(file_path, 'r') as file:
        hex_data = file.read().replace(' ', '').replace('\n', '')
    return hex_data


def hex_to_bytes(hex_data):
    return binascii.unhexlify(hex_data)


def save_bytes_as_image(byte_data, output_path):
    with open(output_path, 'wb') as image_file:
        image_file.write(byte_data)


if __name__ == "__main__":
    hex_file_path = 'rec_txt/saveByteArray.txt'
    output_image_path = 'rec_txt/output_image.jpg'

    hex_data = read_hex_from_file(hex_file_path)
    byte_data = hex_to_bytes(hex_data)
    save_bytes_as_image(byte_data, output_image_path)

    print(f'Image saved to {output_image_path}')
