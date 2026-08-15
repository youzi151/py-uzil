import os
import json

_key_to_inst = {}

def get(name="default", *files):
    """
    取得設定
    :param name: 設定名稱
    :param files: 設定檔路徑
    :return: 設定字典
    """
    if name in _key_to_inst:
        return _key_to_inst[name]
    if name == "default" and len(files) == 0:
        files = ["./config_default.json", "./config_custom.json"]
    cfg = {}
    for file in files:
        if os.path.exists(file):
            with open(file, 'r', encoding='utf-8') as f:
                override_cfg = json.load(f)
                cfg = _merge_dict(cfg, override_cfg)
    _key_to_inst[name] = cfg
    return cfg
        

def _merge_dict(dict_a: dict, dict_b: dict) -> dict:
    """
    合併兩個字典
    :param dict_a: 主要字典
    :param dict_b: 覆蓋字典
    :return: 合併後的字典
    """
    dict_new = {}
    for k, v in dict_b.items():
        if k in dict_a:
            v_a = dict_a[k]
            if isinstance(v, dict) and isinstance(v_a, dict):
                dict_new[k] = _merge_dict(v_a, v)
            else:
                dict_new[k] = v
        else:
            dict_new[k] = v
    return dict_new