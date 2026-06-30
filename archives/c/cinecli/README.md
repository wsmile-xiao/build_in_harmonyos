# cinecli

🎬 **CineCLI** — 一个跨平台的命令行电影浏览器和 torrent 启动器。

## 描述

CineCLI 是一个基于 Python 的 CLI 工具，用于搜索电影、查看电影详情、并直接从终端启动磁力链接或下载 torrent 文件。

## 特性

- 🔍 从 YTS 搜索电影
- 🎥 查看详细的影片信息
- 🧲 直接启动磁力链接到 torrent 客户端
- 📦 下载 .torrent 文件
- ⚡ 自动选择最佳 torrent（最高质量+健康种子）
- 🖥 跨平台支持（Linux、macOS、Windows）
- 🎨 简洁美观的终端 UI

## 技术栈

- **Python 3.9+**
- **Typer** — CLI 框架
- **Rich** — 终端 UI
- **Requests** — API 通信

## 构建说明

cinecli 是纯 Python 项目，不需要传统的 C/C++ 编译流程。

**构建方式**: Python wheel
**安装方式**: `pip install cinecli-0.1.2-py3-none-any.whl`

## 依赖

- typer >= 0.9
- rich >= 13.0
- requests >= 2.28

所有依赖会在安装 wheel 时自动处理。

## 使用方法

```bash
# 搜索电影
python3 -c "from cinecli.cli import app; app(['search', 'matrix'])"

# 观看电影
python3 -c "from cinecli.cli import app; app(['watch', '3525'])"

# 交互模式
python3 -c "from cinecli.cli import app; app(['interactive'])"
```

## 许可证

MIT