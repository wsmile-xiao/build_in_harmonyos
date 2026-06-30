# yt-dlp 2026.03.17 编译记录

## 编译概述

| 项目 | 内容 |
|------|------|
| 软件 | yt-dlp |
| 版本 | 2026.03.17 |
| 构建系统 | Python zipapp |
| 状态 | published |
| 日期 | 2026-05-20 |

## 编译步骤

### Step 1: 源码获取

- 源码包：yt-dlp-2026.03.17.tar.gz
- 来源：https://github.com/yt-dlp/yt-dlp/releases/download/2026.03.17/
- SHA256：c74f56fc88a7f9b7c995646f30538974a03dd7609f55257b20594fdeeb1e13df

### Step 2: 构建分析

yt-dlp 是一个 Python 软件，以 zipapp 格式分发。主要可执行文件 `yt-dlp` 是一个自包含的 Python 包，包含所有必要的模块。

- 文件类型：Python 3 script (zipapp)
- 大小：3.2 MB
- 依赖：Python 3.8+

### Step 3: 安装测试

```bash
# 安装到测试目录
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp yt-dlp $TEST_PREFIX/$DEFAULT_PREFIX/bin/
chmod +x $TEST_PREFIX/$DEFAULT_PREFIX/bin/yt-dlp

# 验证
$TEST_PREFIX/$DEFAULT_PREFIX/bin/yt-dlp --version
# 输出：2026.03.17
```

### Step 4: 预编译包制作

由于 yt-dlp 是 Python 脚本，无需 ELF 签名、strip、RPATH 设置等步骤。

打包内容：
- bin/yt-dlp
- share/man/man1/yt-dlp.1
- share/bash-completion/completions/yt-dlp

### Step 5: 本地部署验证

```bash
# 安装到本地 ~/usr/local
cp yt-dlp $DEFAULT_PREFIX/bin/
$DEFAULT_PREFIX/bin/yt-dlp --version
# 输出：2026.03.17
```

## 问题记录

无。yt-dlp 在 OpenHarmony 上运行无需任何修改。

## 知识提取

- yt-dlp 是 Python zipapp，自包含，无外部依赖
- Python 软件打包流程不同于 C/C++ 软件：
  - 无 configure/make 步骤
  - 无 ELF 签名/strip/RPATH
  - 直接复制文件即可