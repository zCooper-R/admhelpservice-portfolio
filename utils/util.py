import base64


def decode_string(string):
    decoded_string = base64.b64decode(string)
    return decoded_string.decode('utf-8')


def encode_string(string):
    encoded_string = base64.b64encode(string.encode('utf-8'))
    return encoded_string.decode('utf-8')
