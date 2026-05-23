#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快手视频爬虫 - 数据存储模块
"""
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any


@dataclass
class Author:
    """博主信息"""
    user_id: str
    name: str
    avatar: str = ""
    description: str = ""
    followed_at: str = ""
    last_sync_at: str = ""


@dataclass
class Video:
    """视频信息"""
    video_id: str
    author_id: str
    author_name: str
    title: str
    description: str
    video_url: str
    cover_url: str
    publish_time: int  # 时间戳
    duration: float = 0.0
    like_count: int = 0
    view_count: int = 0
    downloaded: bool = False
    downloaded_path: str = ""
    downloaded_at: str = ""


class KuaishouDatabase:
    """快手爬虫数据库"""
    
    def __init__(self, db_file: Path):
        self.db_file = db_file
        self.data = self._load_data()
    
    def _load_data(self) -> Dict[str, Any]:
        """加载数据"""
        if self.db_file.exists():
            with open(self.db_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "authors": {},
            "videos": {},
            "sync_history": []
        }
    
    def _save_data(self):
        """保存数据"""
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def add_author(self, author: Author):
        """添加或更新博主"""
        self.data["authors"][author.user_id] = asdict(author)
        self._save_data()
    
    def get_author(self, user_id: str) -> Optional[Author]:
        """获取博主信息"""
        if user_id in self.data["authors"]:
            data = self.data["authors"][user_id]
            return Author(**data)
        return None
    
    def get_all_authors(self) -> List[Author]:
        """获取所有博主"""
        return [Author(**data) for data in self.data["authors"].values()]
    
    def add_video(self, video: Video):
        """添加或更新视频"""
        self.data["videos"][video.video_id] = asdict(video)
        self._save_data()
    
    def get_video(self, video_id: str) -> Optional[Video]:
        """获取视频"""
        if video_id in self.data["videos"]:
            data = self.data["videos"][video_id]
            return Video(**data)
        return None
    
    def get_author_videos(self, author_id: str) -> List[Video]:
        """获取博主的所有视频"""
        return [
            Video(**data) 
            for data in self.data["videos"].values()
            if data["author_id"] == author_id
        ]
    
    def get_newest_video_timestamp(self, author_id: str) -> int:
        """获取博主最新视频的时间戳"""
        videos = self.get_author_videos(author_id)
        if not videos:
            return 0
        return max(v.publish_time for v in videos)
    
    def is_video_downloaded(self, video_id: str) -> bool:
        """检查视频是否已下载"""
        video = self.get_video(video_id)
        return video.downloaded if video else False
    
    def mark_video_downloaded(self, video_id: str, downloaded_path: str):
        """标记视频已下载"""
        if video_id in self.data["videos"]:
            self.data["videos"][video_id]["downloaded"] = True
            self.data["videos"][video_id]["downloaded_path"] = downloaded_path
            self.data["videos"][video_id]["downloaded_at"] = datetime.now().isoformat()
            self._save_data()
    
    def add_sync_history(self, sync_type: str, details: str):
        """添加同步历史"""
        self.data["sync_history"].append({
            "time": datetime.now().isoformat(),
            "type": sync_type,
            "details": details
        })
        self._save_data()
