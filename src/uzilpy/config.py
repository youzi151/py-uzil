import os
import json

_key_to_inst = {}

root_dir = "."

def use(name="default", use_cached=True, files=None):
    """
    取得設定
    :param name: 設定名稱
    :param use_cached: 是否使用快取
    :param files: 設定檔路徑
    :return: 設定字典
    """
    if use_cached and name in _key_to_inst:
        return _key_to_inst[name]
    
    if files is None:
        files = [
            os.path.join(root_dir, "config_default.json"),
            os.path.join(root_dir, "config_custom.json"),
            os.path.join(root_dir, "config_runtime.json")
        ]
    
    cfg = {}
    for file in files:
        if os.path.exists(file):
            with open(file, 'r', encoding='utf-8') as f:
                override_cfg = json.load(f)
                cfg = merge_dict(cfg, override_cfg)
    _key_to_inst[name] = cfg
    return cfg

def save(file_path=None, cfg_dict={}):
    """
    儲存設定
    :param file_path: 設定檔路徑
    :param cfg_dict: 設定字典
    """
    if file_path is None:
        file_path = os.path.join(root_dir, "config_runtime.json")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(cfg_dict, f, ensure_ascii=False, indent=4)

def load(file_path=None) -> dict:
    """
    載入設定
    :param file_path: 設定檔路徑
    :return: 設定字典
    """
    if file_path is None:
        file_path = os.path.join(root_dir, "config_runtime.json")
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            cfg_dict = json.load(f)
            return cfg_dict
    return {}

def merge_dict(dict_a: dict, dict_b: dict) -> dict:
    """
    合併兩個字典
    :param dict_a: 主要字典
    :param dict_b: 覆蓋字典
    :return: 合併後的字典
    """
    dict_new = {k : v for k, v in dict_a.items() if k not in dict_b}

    for k, v in dict_b.items():
        if k in dict_a:
            v_a = dict_a[k]
            if isinstance(v, dict) and isinstance(v_a, dict):
                dict_new[k] = merge_dict(v_a, v)
            else:
                dict_new[k] = v
        else:
            dict_new[k] = v
    return dict_new