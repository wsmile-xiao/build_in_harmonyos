# streamlink

## 软件简介

Streamlink 是一个命令行工具，用于从各种流媒体服务中提取视频流并将其传输到视频播放器。

- **官方网站**: https://streamlink.github.io/
- **源码仓库**: https://github.com/streamlink/streamlink
- **功能**: 支持数百个流媒体网站的直播流提取

## 编译版本

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 8.4.0 | published | 2026-05-21 | Python 项目，需依赖 libxml2/libxslt |

## 编译说明

### 构建系统

Python 项目，使用 pip + pyproject.toml 构建。

### 依赖要求

**系统库依赖（必须预编译）**：
- libxml2 >= 2.15.3
- libxslt >= 1.1.45

**Python 包依赖（pip 自动安装）**：
- lxml >= 6.0.0
- pycryptodome >= 3.4.3
- PySocks >= 1.5.6
- trio >= 0.22.0
- trio-websocket >= 0.9.0
- requests >= 2.30.0

### 编译命令

```bash
# 1. 安装系统依赖（libxml2/libxslt）
curl -k -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libxml2 2.15.3
curl -k -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libxslt 1.1.45

# 2. 设置环境变量
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
export LD_LIBRARY_PATH="$HOME/usr/local/lib:$LD_LIBRARY_PATH"

# 3. 安装 Python 包
python3 -m pip install lxml pycryptodome PySocks trio trio-websocket

# 4. 安装 streamlink
python3 -m pip install --prefix=$HOME/usr/local streamlink==8.4.0
```

## 验证方法

```bash
streamlink --version
# 输出: streamlink 8.4.0
```

## 使用示例

```bash
# 从 YouTube 提取直播流并播放
streamlink --player mpv https://www.youtube.com/watch?v=VIDEO_ID best

# 列出可用流质量
streamlink https://www.youtube.com/watch?v=VIDEO_ID
```

## 注意事项

1. **依赖库顺序**：必须先安装 libxml2/libxslt，才能编译 lxml
2. **C 扩展编译**：lxml 和 pycryptodome 包含 C 扩展，需要系统库支持
3. **Python 版本**：需要 Python >= 3.10

## 参考链接

- [官方文档](https://streamlink.github.io/)
- [安装指南](https://streamlink.github.io/install.html)
- [CLI 文档](https://streamlink.github.io/cli.html)