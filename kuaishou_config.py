#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快手视频爬虫 - 配置文件
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
DATABASE_FILE = BASE_DIR / "kuaishou_data.json"
DOWNLOAD_DIR = BASE_DIR / "downloads"

# 默认配置
DEFAULT_CONFIG = {
    "headers": {
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Origin": "https://www.kuaishou.com",
        "Referer": "https://www.kuaishou.com",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    },
    "cookies": {},
    "download_dir": str(DOWNLOAD_DIR),
    "concurrent_downloads": 3,
}


def load_config():
    """加载配置文件"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        return {**DEFAULT_CONFIG, **config}
    return DEFAULT_CONFIG


def save_config(config):
    """保存配置文件"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"配置已保存到 {CONFIG_FILE}")
