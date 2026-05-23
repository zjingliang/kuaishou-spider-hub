#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快手API模块 - 使用urllib实现（修复IPv6问题）
"""
import json
import gzip
import ssl
import re
import urllib.request
import urllib.parse
import socket
import time
from typing import Dict, Any, List
from dataclasses import dataclass

from kuaishou_config import load_config


@dataclass
class Author:
    """博主信息"""
    user_id: str
    name: str
    avatar: str = ""
    description: str = ""


@dataclass
class Video:
    """视频信息"""
    video_id: str
    title: str
    author_id: str
    author_name: str
    cover_url: str = ""
    video_url: str = ""
    publish_time: int = 0
    view_count: int = 0
    like_count: int = 0


class KuaishouAPI:
    """快手API"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or load_config()
        self.cookie_header = self._build_cookie_string()
        
        # SSL上下文
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        
        # 默认请求头
        self.default_headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Content-Type": "application/json;charset=UTF-8",
            "Cookie": self.cookie_header,
            "Host": "www.kuaishou.com",
            "Origin": "https://www.kuaishou.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
            "sec-ch-ua": "\"Chromium\";v=\"148\", \"Google Chrome\";v=\"148\", \"Not/A)Brand\";v=\"99\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        
        # 缓存IPv4地址
        self.ipv4_address = self._resolve_ipv4()
    
    def _resolve_ipv4(self) -> str:
        """解析快手服务器的IPv4地址"""
        try:
            addrinfo = socket.getaddrinfo("www.kuaishou.com", 443, socket.AF_INET, socket.SOCK_STREAM)
            if addrinfo:
                return addrinfo[0][4][0]
        except Exception as e:
            print(f"解析IPv4失败: {e}")
        return "www.kuaishou.com"
    
    def _build_cookie_string(self) -> str:
        """构建Cookie字符串"""
        cookies = self.config.get("cookies", {})
        if isinstance(cookies, str):
            return cookies.strip()
        return "; ".join([f"{k}={v}" for k, v in cookies.items()])
    
    def _make_request(self, url: str, data: Dict = None, referer: str = None) -> Dict[str, Any]:
        """发送请求（强制使用IPv4）"""
        headers = self.default_headers.copy()
        if referer:
            headers["Referer"] = referer
        
        # 使用IPv4地址构建请求URL
        parsed_url = urllib.parse.urlparse(url)
        if parsed_url.hostname:
            url = url.replace(parsed_url.hostname, self.ipv4_address)
        
        req_data = json.dumps(data, separators=(',', ':')).encode('utf-8') if data else None
        req = urllib.request.Request(url, data=req_data, headers=headers, method="POST" if data else "GET")
        
        response = urllib.request.urlopen(req, timeout=30, context=self.ssl_ctx)
        
        raw_data = response.read()
        if response.info().get('Content-Encoding') == 'gzip':
            raw_data = gzip.decompress(raw_data)
        
        return json.loads(raw_data.decode('utf-8'))
    
    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本，移除emoji"""
        if not text:
            return ""
        emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"
                               u"\U0001F300-\U0001F5FF"
                               u"\U0001F680-\U0001F6FF"
                               u"\U0001F1E0-\U0001F1FF"
                               "]+", flags=re.UNICODE)
        cleaned = emoji_pattern.sub(r'', text).strip()
        return cleaned if cleaned else text.strip()
    
    def get_following_list(self, pcursor: str = "") -> Dict[str, Any]:
        """获取关注列表"""
        url = "https://www.kuaishou.com/rest/v/relation/fol"
        data = {"pcursor": pcursor, "ftype": 1}
        return self._make_request(url, data, "https://www.kuaishou.com/profile/followed")
    
    def get_author_feed(self, user_id: str, pcursor: str = "") -> Dict[str, Any]:
        """获取博主的视频列表"""
        url = "https://www.kuaishou.com/rest/v/profile/feed"
        data = {"user_id": user_id, "pcursor": pcursor, "page": "profile"}
        return self._make_request(url, data, f"https://www.kuaishou.com/profile/{user_id}")
    
    def _get_video_url(self, photo: Dict) -> str:
        """从photo数据中提取视频URL"""
        # 尝试从manifest获取（manifest已经是字典，不需要json解析）
        manifest = photo.get('manifest', {})
        if isinstance(manifest, dict):
            # 检查adaptationSet
            if 'adaptationSet' in manifest:
                adaptation_sets = manifest['adaptationSet']
                if isinstance(adaptation_sets, list) and adaptation_sets:
                    for adaptation in adaptation_sets:
                        if isinstance(adaptation, dict) and 'representation' in adaptation:
                            representations = adaptation['representation']
                            if isinstance(representations, list) and representations:
                                for rep in representations:
                                    if isinstance(rep, dict) and 'url' in rep:
                                        return rep['url']
            
            # 检查playInfo
            if 'playInfo' in manifest:
                play_info = manifest['playInfo']
                if isinstance(play_info, list) and play_info:
                    for info in play_info:
                        if isinstance(info, dict) and 'url' in info:
                            return info['url']
        
        # 尝试从photoUrls获取（这是包含字典的列表）
        photo_urls = photo.get('photoUrls', [])
        if isinstance(photo_urls, list):
            for item in photo_urls:
                if isinstance(item, dict) and 'url' in item:
                    return item['url']
        
        # 尝试其他字段
        for key in ['videoUrl', 'video_url', 'url', 'playUrl', 'downloadUrl']:
            if key in photo:
                value = photo[key]
                if isinstance(value, str):
                    return value
                elif isinstance(value, dict) and 'url' in value:
                    return value['url']
        
        return None
    
    def get_all_following_authors(self) -> List[Author]:
        """获取所有关注的博主"""
        authors = []
        pcursor = ""
        
        while True:
            try:
                data = self.get_following_list(pcursor)
                
                if not isinstance(data, dict):
                    print(f"API返回数据格式错误: {type(data)}")
                    break
                
                result = data.get("result")
                if result != 1:
                    print(f"API返回错误: {data}")
                    break
                
                users = data.get("fols", [])
                if not isinstance(users, list):
                    print(f"用户列表格式错误: {type(users)}")
                    break
                
                if not users:
                    break
                
                for user in users:
                    if not isinstance(user, dict):
                        print(f"用户数据格式错误: {type(user)}")
                        continue
                    
                    user_id = user.get("user_id", "") or user.get("id", "")
                    if not user_id:
                        continue
                    
                    name = self.clean_text(user.get("user_name", "") or user.get("name", "") or "")
                    if not name:
                        name = f"用户{user_id[:8]}"
                    
                    author = Author(
                        user_id=user_id,
                        name=name,
                        avatar=user.get("headerUrl", "") or user.get("headurl", "") or "",
                        description=self.clean_text(user.get("text", "") or user.get("user_text", "") or "")
                    )
                    authors.append(author)
                
                pcursor = data.get("pcursor", "")
                if pcursor == "no_more":
                    break
                    
                time.sleep(0.5)
                
            except Exception as e:
                print(f"获取关注列表失败: {e}")
                break
        
        return authors
    
    def get_author_all_videos(self, user_id: str, after_timestamp: int = 0) -> List[Video]:
        """获取博主的所有视频"""
        videos = []
        pcursor = ""
        
        while True:
            try:
                data = self.get_author_feed(user_id, pcursor)
                
                if not isinstance(data, dict):
                    print(f"视频列表数据格式错误: {type(data)}")
                    break
                
                feeds = data.get("feeds", [])
                if not isinstance(feeds, list):
                    print(f"feeds格式错误: {type(feeds)}")
                    break
                
                if not feeds:
                    break
                
                for feed in feeds:
                    if not isinstance(feed, dict):
                        print(f"feed格式错误: {type(feed)}")
                        continue
                    
                    photo = feed.get("photo", {})
                    if not isinstance(photo, dict):
                        print(f"photo格式错误: {type(photo)}")
                        continue
                    
                    timestamp = photo.get("timestamp", 0)
                    if timestamp and after_timestamp and timestamp < after_timestamp:
                        return videos
                    
                    video_url = self._get_video_url(photo)
                    
                    video = Video(
                        video_id=photo.get("id", ""),
                        title=self.clean_text(photo.get("caption", "")) or "无标题",
                        author_id=user_id,
                        author_name=self.clean_text(photo.get("authorName", "") or photo.get("user_name", "")),
                        cover_url=photo.get("coverUrl", "") or photo.get("cover_thumbnail_url", ""),
                        video_url=video_url,
                        publish_time=timestamp // 1000 if timestamp else 0,
                        view_count=photo.get("viewCount", 0) or 0,
                        like_count=photo.get("likeCount", 0) or 0
                    )
                    videos.append(video)
                
                pcursor = data.get("pcursor", "")
                if pcursor == "no_more" or not pcursor:
                    break
                    
                time.sleep(0.5)
                
            except Exception as e:
                print(f"获取视频列表失败: {e}")
                break
        
        return videos
    
    def search_videos(self, keyword: str, start_time: int = 0, end_time: int = 0, count: int = 20) -> List[Video]:
        """搜索视频"""
        url = "https://www.kuaishou.com/rest/v1/search/video"
        data = {
            "keyword": keyword,
            "count": count,
            "startTime": start_time,
            "endTime": end_time
        }
        result = self._make_request(url, data, "https://www.kuaishou.com/search")
        
        videos = []
        if result.get("result") == 1:
            items = result.get("items", [])
            for item in items:
                photo = item.get("photo", {})
                video = Video(
                    video_id=photo.get("id", ""),
                    title=self.clean_text(photo.get("caption", "")) or "无标题",
                    author_id=photo.get("authorId", ""),
                    author_name=self.clean_text(photo.get("authorName", "")),
                    cover_url=photo.get("coverUrl", ""),
                    video_url=self._get_video_url(photo),
                    publish_time=photo.get("timestamp", 0) // 1000,
                    view_count=photo.get("viewCount", 0),
                    like_count=photo.get("likeCount", 0)
                )
                videos.append(video)
        
        return videos
