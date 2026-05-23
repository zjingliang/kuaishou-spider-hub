#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快手视频爬虫 - 主程序入口
"""
import sys
import argparse
from datetime import datetime
from pathlib import Path

from kuaishou_config import save_config, CONFIG_FILE
from kuaishou_crawler import KuaishouCrawler


def print_menu():
    """打印菜单"""
    print("\n" + "="*50)
    print("        快手视频爬虫 v1.0")
    print("="*50)
    print("1. 首次下载：添加博主并下载所有视频")
    print("2. 增量更新：检查并下载博主的最新视频")
    print("3. 全部更新：为所有已保存的博主更新最新视频")
    print("4. 搜索下载：按关键词+时间范围搜索下载")
    print("5. 批量导入：从文件导入博主ID")
    print("6. 设置Cookies")
    print("0. 退出")
    print("="*50)


def set_cookies():
    """设置Cookies"""
    print("\n请输入Cookies（从浏览器复制）:")
    print("提示：按回车跳过，或直接粘贴完整的Cookie字符串")
    
    cookie_str = input("> ").strip()
    
    if not cookie_str:
        print("未输入Cookies")
        return
    
    # 解析Cookie字符串
    cookies = {}
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            key, value = item.split("=", 1)
            cookies[key.strip()] = value.strip()
    
    from kuaishou_config import load_config
    config = load_config()
    config["cookies"] = cookies
    save_config(config)
    
    print(f"已保存 {len(cookies)} 个Cookie项到 {CONFIG_FILE}")


def function1_download_all(crawler: KuaishouCrawler):
    """功能1：首次下载"""
    print("\n--- 首次下载 ---")
    user_id = input("请输入博主ID (user_id): ").strip()
    
    if not user_id:
        print("未输入博主ID")
        return
    
    crawler.download_all_videos_for_author(user_id)


def function2_incremental(crawler: KuaishouCrawler):
    """功能2：增量更新单个博主"""
    print("\n--- 增量更新 ---")
    user_id = input("请输入博主ID (user_id): ").strip()
    
    if not user_id:
        print("未输入博主ID")
        return
    
    crawler.download_new_videos_for_author(user_id)


def function3_incremental_all(crawler: KuaishouCrawler):
    """功能3：全部更新"""
    print("\n--- 全部更新 ---")
    crawler.download_new_videos_all_authors()


def function4_search_download(crawler: KuaishouCrawler):
    """功能4：搜索下载"""
    print("\n--- 搜索下载 ---")
    print("说明：搜索功能需要您补充快手搜索API信息")
    print("当前版本仅作框架展示")
    
    keywords_input = input("请输入关键词（多个用逗号分隔）: ").strip()
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
    
    if not keywords:
        print("未输入关键词")
        return
    
    # 输入时间范围
    start_str = input("请输入开始时间（格式: YYYY-MM-DD HH:MM）: ").strip()
    end_str = input("请输入结束时间（格式: YYYY-MM-DD HH:MM）: ").strip()
    
    try:
        start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
        end_time = datetime.strptime(end_str, "%Y-%m-%d %H:%M")
    except ValueError:
        print("时间格式错误")
        return
    
    crawler.search_and_download_videos(keywords, start_time, end_time)


def function5_import_authors(crawler: KuaishouCrawler):
    """功能5：批量导入"""
    print("\n--- 批量导入 ---")
    file_path = input("请输入博主ID文件路径: ").strip()
    
    if not file_path:
        print("未输入文件路径")
        return
    
    if not Path(file_path).exists():
        print(f"文件不存在: {file_path}")
        return
    
    crawler.import_authors_from_file(file_path)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="快手视频爬虫")
    parser.add_argument("--mode", type=int, help="直接运行模式 (0-6)")
    args = parser.parse_args()
    
    crawler = KuaishouCrawler()
    
    if args.mode is not None:
        # 命令行模式
        mode = args.mode
    else:
        # 交互式模式
        while True:
            print_menu()
            choice = input("\n请选择功能 (0-6): ").strip()
            
            try:
                mode = int(choice)
            except ValueError:
                print("无效输入")
                continue
            
            if mode == 0:
                print("退出程序")
                break
            elif mode == 1:
                function1_download_all(crawler)
            elif mode == 2:
                function2_incremental(crawler)
            elif mode == 3:
                function3_incremental_all(crawler)
            elif mode == 4:
                function4_search_download(crawler)
            elif mode == 5:
                function5_import_authors(crawler)
            elif mode == 6:
                set_cookies()
            else:
                print("无效选项")
    
    print("\n感谢使用！")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断，退出程序")
        sys.exit(0)
    except Exception as e:
        print(f"\n程序出错: {e}")
        import traceback
        traceback.print_exc()
