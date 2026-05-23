# 快手视频爬虫

快手视频爬虫，支持关注博主全量下载、增量更新、GUI界面操作。

## 功能特性

- **首次下载**：输入博主ID，下载该博主的所有历史视频
- **增量更新**：每天运行只下载博主发布的新视频
- **批量更新**：为所有已保存的博主批量更新最新视频
- **GUI界面**：图形化操作界面，支持暂停/继续/停止控制
- **实时日志**：GUI界面实时显示下载进度和日志

## 项目结构

```
kuaishou-spider/
├── kuaishou_api.py         # 快手API交互模块
├── kuaishou_config.py      # 配置模块
├── kuaishou_crawler.py     # 爬虫核心模块
├── kuaishou_database.py    # 数据存储模块
├── kuaishou_gui.py         # GUI图形界面
├── kuaishou_main.py        # 命令行主程序
├── main.py                 # 程序入口
├── requirements.txt        # Python依赖
├── config_example.json     # 配置文件示例
└── authors_example.txt    # 博主ID示例
```

## 环境要求

- Python 3.8+
- Windows/Linux/macOS

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 配置Cookies

运行程序后会自动提示输入Cookies，或手动编辑 `config.json`：

1. 在浏览器中打开快手网页版并登录
2. 按F12打开开发者工具
3. 在Network标签中找到任意请求，复制Cookie
4. 将Cookie填入配置文件

### 2. 命令行模式

```bash
python main.py
```

### 3. GUI界面

```bash
python kuaishou_gui.py
```

## 功能说明

| 功能 | 说明 |
|------|------|
| 首次下载 | 添加博主并下载所有历史视频 |
| 增量更新 | 只下载博主发布的新视频 |
| 全部更新 | 为所有已保存的博主批量更新 |
| 搜索下载 | 按关键词搜索并下载视频 |
| 批量导入 | 从文件批量导入博主ID |

## 免责声明

本项目仅供学习交流使用，请勿用于商业用途或任何违法活动。使用本项目产生的任何问题由使用者自行承担。

## License

MIT License
