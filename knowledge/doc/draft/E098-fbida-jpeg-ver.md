# E098: fbida JPEG_VER 版本检测脚本失败（缺少 cpp 预处理器）

> **结构化数据**: [graph/draft/E098-fbida-jpeg-ver.kv](../../graph/draft/E098-fbida-jpeg-ver.kv) | **原则**: P-DEPENDENCY-001, P-CONFIGURATION-001
> **严重度**: 🟡 warning | **分类**: dependency | **自动修复**: ✅ semi-auto

---

## 错误特征

```
scripts/jpeg-version.sh: line 5: cpp: not found
JPEG_VER: undefined
test: -eq: JVERSION: syntax error
make: JPEG_VER is not set
```

## 根因

fbida 的 jpeg-version.sh 脚本需要 cpp 预处理器来检测 JPEG 库版本：
1. 脚本使用 `cpp` 预处理器处理 jpeglib.h 来提取 JPEG_LIB_VERSION
2. 如果系统没有安装 cpp，脚本会失败
3. 即使有 cpp，脚本也可能因为路径问题而失败

解决方法：手动设置 JPEG_VER 环境变量，跳过自动检测。

## 解决方案

**推荐方案**：手动设置 JPEG_VER

```bash
# Step 1: 确定 libjpeg 版本
grep JPEG_LIB_VERSION /usr/local/include/jpeglib.h | head -1
# 输出: #define JPEG_LIB_VERSION  62

# Step 2: 手动设置
export JPEG_VER=62

# Step 3: 运行配置
make config

# Step 4: 验证配置
grep JPEG_VER Make.config
```

**备选方案**：安装 cpp 预处理器

```bash
# Debian/Ubuntu
sudo apt-get install cpp

# OpenHarmony: 检查是否可用，或使用手动设置方案
```

## 版本对应表

| libjpeg 版本 | JPEG_LIB_VERSION | JPEG_VER |
|-------------|------------------|----------|
| libjpeg 6b | 62 | 62 |
| libjpeg-turbo 1.x | 62 | 62 |
| libjpeg-turbo 2.x | 62 | 62 |
| libjpeg-turbo 3.x | 62 | 62 |

## 验证命令

```bash
# 检查 cpp 是否存在
which cpp
# 输出: /usr/bin/cpp 或 "not found"

# 测试版本检测脚本
scripts/jpeg-version.sh 2>&1
# 输出: 失败信息

# 检查 libjpeg 版本
grep JPEG_LIB_VERSION /usr/local/include/jpeglib.h 2>&1 | head -3
```

## 涉及软件

fbida、所有依赖 jpeg-version.sh 或类似版本检测脚本的项目。

## 相关模式

- [E006](E006.md) — 依赖版本不匹配
- [E007](E007.md) — 平台不识别
- [E097](E097-fbida-autoconf.md) — fbida 自定义 autoconf 系统（前置原因）

---
*doc/draft/E098-fbida-jpeg-ver.md · knowledge graph v2 · 2026-06-12*