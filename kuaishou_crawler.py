#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快手视频爬虫核心模块
"""
import json
import ssl
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from threading import Event

from kuaishou_api import KuaishouAPI, Author, Video
from kuaishou_config import load_config, save_config, BASE_DIR


class KuaishouCrawler:
    """快手爬虫核心类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or load_config()
        self.api = KuaishouAPI(self.config)
        self.download_dir = BASE_DIR / "downloads"
        self.download_dir.mkdir(exist_ok=True)
        
        # SSL上下文
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        
        # 下载线程数
        self.max_workers = 3
        
        # 暂停/继续控制
        self.pause_event = Event()
        self.pause_event.set()  # 默认不暂停
        self.stop_event = Event()
    
    def pause_download(self):
        """暂停下载"""
        self.pause_event.clear()
        print("[暂停] 下载已暂停")
    
    def resume_download(self):
        """继续下载"""
        self.pause_event.set()
        print("[继续] 下载已恢复")
    
    def stop_download(self):
        """停止下载"""
        self.stop_event.set()
        self.pause_event.set()  # 唤醒等待中的线程
        print("[停止] 下载已停止")
    
    def is_paused(self):
        """检查是否暂停"""
        return not self.pause_event.is_set()
    
    def is_stopped(self):
        """检查是否停止"""
        return self.stop_event.is_set()
    
    def reset_state(self):
        """重置状态"""
        self.pause_event.set()
        self.stop_event.clear()
    
    @staticmethod
    def sanitize_filename(name: str) -> str:
        """清理文件名"""
        if not name:
            return "无标题"
        # 移除非法字符
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        name = name.strip()
        if len(name) > 80:
            name = name[:80]
        return name
    
    def get_video_save_path(self, video: Video, author: Author) -> Path:
        """获取视频保存路径"""
        try:
            if video.publish_time and video.publish_time > 0:
                publish_date = datetime.fromtimestamp(video.publish_time).strftime("%Y-%m-%d")
            else:
                publish_date = "未知日期"
        except:
            publish_date = "未知日期"
        
        author_name = author.name.strip() if author.name else f"用户{author.user_id[:8]}"
        safe_author_name = self.sanitize_filename(author_name)
        save_dir = self.download_dir / publish_date / f"{safe_author_name}_{author.user_id}"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        safe_title = self.sanitize_filename(video.title or "无标题")
        filename = f"{video.video_id}_{safe_title}.mp4"
        return save_dir / filename
    
    def download_video(self, video: Video, save_path: Path, author: Author) -> bool:
        """下载单个视频（不携带身份信息）"""
        try:
            # 获取视频URL
            video_url = video.video_url
            if not video_url or not isinstance(video_url, str):
                print(f"  [跳过] 无法获取视频URL: {video.title[:30]}")
                return False
            
            # 检查暂停状态
            if self.is_paused():
                print(f"  [等待] 等待恢复下载: {video.title[:30]}")
                self.pause_event.wait()
            
            if self.is_stopped():
                print(f"  [停止] 下载已停止: {video.title[:30]}")
                return False
            
            # 下载视频（不携带Cookie等身份信息）
            req = urllib.request.Request(
                video_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://www.kuaishou.com/",
                    "Accept": "*/*",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept-Encoding": "identity",
                    "Connection": "keep-alive"
                }
            )
            
            with urllib.request.urlopen(req, timeout=60, context=self.ssl_ctx) as response:
                video_data = response.read()
            
            # 保存文件
            with open(save_path, 'wb') as f:
                f.write(video_data)
            
            size = len(video_data) / (1024 * 1024)
            print(f"  [成功] {video.title[:30]} ({size:.1f}MB)")
            return True
            
        except Exception as e:
            print(f"  [失败] {video.title[:30]}: {e}")
            return False
    
    def get_author_videos(self, author: Author) -> List[Video]:
        """获取博主视频列表"""
        try:
            return self.api.get_author_all_videos(author.user_id)
        except Exception as e:
            print(f"  获取视频列表失败: {e}")
            return []
    
    def download_author_videos(self, author: Author, full_download: bool = True) -> int:
        """下载博主视频（带进度显示）"""
        videos = self.get_author_videos(author)
        if not videos:
            print(f"  无视频")
            return 0
        
        total_videos = len(videos)
        print(f"  获取到 {total_videos} 个视频")
        
        downloaded = 0
        skipped = 0
        
        for idx, video in enumerate(videos, 1):
            # 检查停止状态
            if self.is_stopped():
                print(f"  [停止] 已停止下载")
                break
            
            # 检查暂停状态
            if self.is_paused():
                print(f"  [等待] 等待恢复下载...")
                self.pause_event.wait()
                if self.is_stopped():
                    break
            
            save_path = self.get_video_save_path(video, author)
            
            # 跳过已存在的
            if save_path.exists():
                skipped += 1
                continue
            
            # 显示进度（视频少于20个时每个都显示，否则每10个显示一次）
            if total_videos <= 20 or idx % 10 == 0 or idx == total_videos:
                progress = idx / total_videos * 100
                progress_bar = "[" + "=" * int(progress // 5) + " " * int((100 - progress) // 5) + "]"
                print(f"  进度: {progress_bar} {idx}/{total_videos} ({progress:.1f}%)")
            
            if self.download_video(video, save_path, author):
                downloaded += 1
            
            time.sleep(0.3)  # 避免请求过快
        
        print()  # 换行
        print(f"  下载: {downloaded} | 跳过: {skipped} | 失败: {total_videos - downloaded - skipped}")
        
        return downloaded
    
    def fetch_and_save_following(self) -> List[Author]:
        """获取并保存关注列表"""
        print("\n" + "="*60)
        print("获取关注列表")
        print("="*60)
        
        authors = self.api.get_all_following_authors()
        print(f"找到 {len(authors)} 个关注的博主")
        
        # 保存到文件
        data_file = BASE_DIR / "kuaishou_data.json"
        existing_data = {}
        if data_file.exists():
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except Exception as e:
                print(f"  读取现有数据失败: {e}")
        
        # 确保authors字段是列表
        if 'authors' in existing_data and not isinstance(existing_data['authors'], list):
            existing_data['authors'] = []
        
        existing_ids = set()
        for a in existing_data.get('authors', []):
            if isinstance(a, dict) and 'user_id' in a:
                existing_ids.add(a['user_id'])
        
        new_count = 0
        for author in authors:
            if author.user_id not in existing_ids:
                if 'authors' not in existing_data:
                    existing_data['authors'] = []
                existing_data['authors'].append(asdict(author))
                new_count += 1
        
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        
        print(f"新增 {new_count} 个博主")
        return authors
    
    def first_time_setup(self):
        """首次完整流程"""
        print("\n" + "="*60)
        print("快手视频爬虫 - 首次使用")
        print("="*60)
        
        # 重置状态
        self.reset_state()
        
        authors = self.fetch_and_save_following()
        
        if not authors:
            print("没有找到关注的博主")
            return
        
        total_authors = len(authors)
        print(f"\n开始下载 {total_authors} 个博主的视频...")
        
        total_downloaded = 0
        for i, author in enumerate(authors, 1):
            # 检查停止状态
            if self.is_stopped():
                print(f"\n[停止] 已停止下载")
                break
            
            print(f"\n[{i}/{total_authors}] 博主: {author.name}")
            downloaded = self.download_author_videos(author, full_download=True)
            total_downloaded += downloaded
            print(f"  下载了 {downloaded} 个视频")
        
        print(f"\n" + "="*60)
        print(f"首次使用完成！共下载 {total_downloaded} 个视频")
        print(f"视频保存在: {self.download_dir}")
        print("="*60)
    
    def update_all_authors(self):
        """增量更新所有博主"""
        print("\n" + "="*60)
        print("增量更新所有博主")
        print("="*60)
        
        # 重置状态
        self.reset_state()
        
        data_file = BASE_DIR / "kuaishou_data.json"
        if not data_file.exists():
            print("没有数据文件，请先运行首次使用")
            return
        
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        authors_data = data.get('authors', [])
        if not authors_data:
            print("没有博主数据")
            return
        
        total_authors = len(authors_data)
        print(f"共有 {total_authors} 个博主")
        
        total_downloaded = 0
        for i, author_dict in enumerate(authors_data, 1):
            # 检查停止状态
            if self.is_stopped():
                print(f"\n[停止] 已停止下载")
                break
            
            author = Author(**author_dict)
            print(f"\n[{i}/{total_authors}] 博主: {author.name}")
            downloaded = self.download_author_videos(author, full_download=False)
            total_downloaded += downloaded
            print(f"  下载了 {downloaded} 个视频")
        
        print(f"\n" + "="*60)
        print(f"增量更新完成！共下载 {total_downloaded} 个视频")
        print("="*60)
    
    def import_authors(self, user_ids: List[str]):
        """批量导入博主"""
        for user_id in user_ids:
            author = Author(user_id=user_id, name=f"用户{user_id[:8]}")
            data_file = BASE_DIR / "kuaishou_data.json"
            existing_data = {}
            if data_file.exists():
                with open(data_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            
            existing_ids = {a['user_id'] for a in existing_data.get('authors', [])}
            if user_id not in existing_ids:
                existing_data.setdefault('authors', []).append(asdict(author))
                with open(data_file, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, ensure_ascii=False, indent=2)
                print(f"已添加博主: {user_id}")
    
    def search_and_download(self, keywords: List[str], start_time: int = 0, end_time: int = 0):
        """搜索并下载视频"""
        # 重置状态
        self.reset_state()
        
        for keyword in keywords:
            print(f"\n搜索关键词: {keyword}")
            videos = self.api.search_videos(keyword, start_time, end_time)
            print(f"找到 {len(videos)} 个视频")
            
            total_videos = len(videos)
            downloaded = 0
            skipped = 0
            
            for idx, video in enumerate(videos, 1):
                if self.is_stopped():
                    break
                
                if self.is_paused():
                    self.pause_event.wait()
                    if self.is_stopped():
                        break
                
                author = Author(
                    user_id=video.author_id,
                    name=video.author_name or f"用户{video.author_id[:8]}"
                )
                save_path = self.get_video_save_path(video, author)
                
                if save_path.exists():
                    skipped += 1
                    continue
                
                # 显示进度（每10个视频输出一次进度）
                if idx % 10 == 0 or idx == total_videos:
                    progress = idx / total_videos * 100
                    progress_bar = "[" + "=" * int(progress // 5) + " " * int((100 - progress) // 5) + "]"
                    print(f"  进度: {progress_bar} {idx}/{total_videos} ({progress:.1f}%)")
                
                if self.download_video(video, save_path, author):
                    downloaded += 1
            
            print()
            print(f"  下载: {downloaded} | 跳过: {skipped}")