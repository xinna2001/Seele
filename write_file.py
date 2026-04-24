import json


def write_dict_to_json(dictionary, file_path):
    """
    将字典数据写入 JSON 文件
    :param dictionary: 要写入的字典数据
    :param file_path: JSON 文件的路径
    """
    if not isinstance(dictionary, dict):
        return
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(dictionary, file, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"写入文件时出错: {e}")


def read_dict_from_json(file_path):
    """
    从 JSON 文件读取数据并返回字典
    :param file_path: JSON 文件的路径
    :return: 读取的字典数据，如果出错则返回 None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        if not isinstance(data, dict):
            return None
        return data
    except FileNotFoundError:
        print(f"错误: 文件 {file_path} 未找到!")
    except json.JSONDecodeError:
        print(f"错误: 无法解析 {file_path} 中的 JSON 数据!")
    except Exception as e:
        print(f"读取文件时出错: {e}")
    return None
    