# -*- coding: utf-8 -*-
"""因子白名单 — 校验/注册（战斗业务特有）"""

import os
import sys
import json

sys.path.insert(0, os.path.join(r'G:\op_design', 'references', 'scripts', 'core'))
from constants import WHITELIST_PATH

_whitelist_cache = None


def load_whitelist():
    """加载因子白名单（缓存）"""
    global _whitelist_cache
    if _whitelist_cache is None:
        if os.path.exists(WHITELIST_PATH):
            with open(WHITELIST_PATH, 'r', encoding='utf-8') as f:
                _whitelist_cache = json.load(f)
        else:
            _whitelist_cache = {}
    return _whitelist_cache


def validate_factor(name):
    """校验因子名 — 白名单内直接通过，不查库

    Returns:
        dict: 因子元数据 {"desc":..., "type":..., "pct":...}，None=未知因子
    """
    wl = load_whitelist()
    return wl.get(name)


def register_factor(name, desc, buff_type=1, pct=0, ref=""):
    """注册新因子到白名单（查库确认后调用，下次不再查）"""
    global _whitelist_cache
    wl = load_whitelist()
    wl[name] = {"desc": desc, "type": buff_type, "pct": pct, "ref": ref}
    with open(WHITELIST_PATH, 'w', encoding='utf-8') as f:
        json.dump(wl, f, ensure_ascii=False, indent=2)
    _whitelist_cache = wl
    print(f"  [REGISTER] 因子 '{name}' ({desc}) 已注册到白名单")
