#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快手视频爬虫 - GUI界面
"""
import sys
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue

from kuaishou_config import load_config, save_config, BASE_DIR
from kuaishou_crawler import KuaishouCrawler


class LogRedirector:
    """重定向print输出到GUI"""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self._check_queue()
    
    def write(self, text):
        if text.strip():
            self.queue.put(text)
    
    def flush(self):
        pass
    
    def _check_queue(self):
        try:
            while True:
                text = self.queue.get_nowait()
                self.text_widget.insert(tk.END, text)
                self.text_widget.see(tk.END)
        except queue.Empty:
            pass
        self.text_widget.after(100, self._check_queue)


class KuaishouGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("快手视频爬虫 v1.0")
        self.root.geometry("900x750")
        
        self.crawler = None
        self.is_running = False
        
        self._build_ui()
        self._init_crawler()
    
    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 配置区域
        config_frame = ttk.LabelFrame(main_frame, text="配置", padding="10")
        config_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        config_frame.columnconfigure(0, weight=1)
        
        ttk.Label(config_frame, text="Cookies:").grid(row=0, column=0, sticky=tk.W)
        self.cookie_text = tk.Text(config_frame, height=3, width=80)
        self.cookie_text.grid(row=1, column=0, columnspan=2, pady=5)
        
        btn_frame = ttk.Frame(config_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=5)
        ttk.Button(btn_frame, text="保存配置", command=self._save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="获取帮助", command=self._show_help).pack(side=tk.LEFT, padx=5)
        
        # 功能区域
        func_frame = ttk.LabelFrame(main_frame, text="功能", padding="10")
        func_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        func_frame.columnconfigure(0, weight=1)
        func_frame.columnconfigure(1, weight=1)
        func_frame.columnconfigure(2, weight=1)
        
        ttk.Button(func_frame, text="首次使用：获取关注并下载所有视频", 
                   command=self._first_time).grid(row=0, column=0, columnspan=3, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(func_frame, text="增量更新：下载所有博主的新视频", 
                   command=self._update).grid(row=1, column=0, columnspan=3, pady=5, sticky=(tk.W, tk.E))
        
        # 控制按钮区域
        control_frame = ttk.LabelFrame(main_frame, text="控制", padding="10")
        control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        control_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(1, weight=1)
        control_frame.columnconfigure(2, weight=1)
        
        self.pause_btn = ttk.Button(control_frame, text="暂停", command=self._pause, state="disabled")
        self.pause_btn.grid(row=0, column=0, pady=5, sticky=(tk.W, tk.E), padx=2)
        
        self.resume_btn = ttk.Button(control_frame, text="继续", command=self._resume, state="disabled")
        self.resume_btn.grid(row=0, column=1, pady=5, sticky=(tk.W, tk.E), padx=2)
        
        self.stop_btn = ttk.Button(control_frame, text="停止", command=self._stop, state="disabled")
        self.stop_btn.grid(row=0, column=2, pady=5, sticky=(tk.W, tk.E), padx=2)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="10")
        log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, state="normal")
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN).grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)
    
    def _init_crawler(self):
        try:
            self.crawler = KuaishouCrawler()
            self.log_redirector = LogRedirector(self.log_text)
            sys.stdout = self.log_redirector
            sys.stderr = self.log_redirector
            
            print("="*50)
            print("快手视频爬虫 v1.0")
            print("="*50)
            
            config = load_config()
            if config.get("cookies"):
                cookie_str = "; ".join([f"{k}={v}" for k, v in config["cookies"].items()])
                self.cookie_text.delete("1.0", tk.END)
                self.cookie_text.insert("1.0", cookie_str)
            print("初始化完成!\n")
        except Exception as e:
            messagebox.showerror("错误", f"初始化失败: {e}")
    
    def _save_config(self):
        try:
            cookie_str = self.cookie_text.get("1.0", tk.END).strip()
            cookies = {}
            for item in cookie_str.split(";"):
                item = item.strip()
                if "=" in item:
                    k, v = item.split("=", 1)
                    cookies[k.strip()] = v.strip()
            
            config = load_config()
            config["cookies"] = cookies
            save_config(config)
            
            self.crawler = KuaishouCrawler(config)
            print(f"配置已保存! ({len(cookies)} 个Cookie项)")
            self.status_var.set("配置已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")
    
    def _show_help(self):
        help_text = """获取Cookies步骤：

1. 打开快手网页版 https://www.kuaishou.com
2. 登录账号
3. 按F12打开开发者工具
4. 切换到 Network 标签
5. 刷新页面
6. 点击任意请求，查看 Headers
7. 复制 Cookie 值
8. 粘贴到上方文本框
9. 点击"保存配置"

注意：Cookies会过期，如报错请重新获取。

使用说明：
- 首次使用：获取关注列表并下载所有视频
- 增量更新：仅下载新增的视频
- 暂停/继续：控制下载进度
- 停止：立即停止当前任务"""
        messagebox.showinfo("帮助", help_text)
    
    def _enable_control_buttons(self):
        """启用控制按钮"""
        self.pause_btn.config(state="normal")
        self.resume_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
    
    def _disable_control_buttons(self):
        """禁用控制按钮"""
        self.pause_btn.config(state="disabled")
        self.resume_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
    
    def _run_task(self, task_func):
        if self.is_running:
            messagebox.showwarning("提示", "任务正在运行中")
            return
        
        self.is_running = True
        self.status_var.set("运行中...")
        self._enable_control_buttons()
        
        def wrapper():
            try:
                task_func()
            except Exception as e:
                print(f"\n错误: {e}")
            finally:
                self.is_running = False
                self.status_var.set("就绪")
                self._disable_control_buttons()
        
        threading.Thread(target=wrapper, daemon=True).start()
    
    def _first_time(self):
        self._run_task(lambda: self.crawler.first_time_setup())
    
    def _update(self):
        self._run_task(lambda: self.crawler.update_all_authors())
    
    def _pause(self):
        if self.crawler:
            self.crawler.pause_download()
            self.pause_btn.config(state="disabled")
            self.resume_btn.config(state="normal")
            self.status_var.set("已暂停")
    
    def _resume(self):
        if self.crawler:
            self.crawler.resume_download()
            self.pause_btn.config(state="normal")
            self.resume_btn.config(state="disabled")
            self.status_var.set("运行中...")
    
    def _stop(self):
        if self.crawler:
            self.crawler.stop_download()
            self._disable_control_buttons()
            self.status_var.set("已停止")


def main():
    root = tk.Tk()
    app = KuaishouGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()