# yt-dlp 2026.03.17 编译笔记

## 软件类型

yt-dlp 是一个 **Python zipapp**（打包的单文件可执行程序），包含完整的 yt_dlp Python 模块。

## 构建流程

### 1. 源码下载

从 GitHub releases 下载 tarball：
- URL: https://github.com/yt-dlp/yt-dlp/releases/download/2026.03.17/yt-dlp.tar.gz
- 大小: 6.2 MB

### 2. 安装步骤

对于 Python zipapp 类型软件，无需传统编译：
```bash
# 直接复制可执行文件到目标目录
cp yt-dlp ~/usr/local/bin/
chmod +x ~/usr/local/bin/yt-dlp
```

### 3. 验证

```bash
~/usr/local/bin/yt-dlp --version
# 输出: 2026.03.17
```

## 平台适配

- 无需修改源码，Python 脚本可直接运行
- 需要确保 Python 3.10+ 已安装

## 运行时依赖

- Python 3.10+ (必需)
- 可选依赖: brotli, certifi, mutagen, pycryptodomex, requests, urllib3, websockets

## 知识提取

无新增平台知识 - Python zipapp 可直接运行。

---

**编译结束**: 2026-05-20
**最终状态**: built
