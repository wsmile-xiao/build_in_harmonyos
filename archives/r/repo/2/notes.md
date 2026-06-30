# repo 编译笔记 — 版本 2

## 编译概述

repo 是 Android 多仓库管理工具，基于 Git 构建。它是一个纯 Python 脚本工具，不需要编译 C/C++ 代码，只需要打包安装。

## 源码获取

- **来源**: GitHub 镜像 (https://github.com/GerritCodeReview/git-repo)
- **原因**: 官方源 gerrit.googlesource.com SSL 证书问题无法下载
- **版本**: setup.py 中定义为 "2"，launcher VERSION 为 (2, 54)

## 编译过程

### 步骤 1: 下载源码

```bash
curl -k -L -o repo.tar.gz "https://github.com/GerritCodeReview/git-repo/archive/refs/heads/main.tar.gz"
tar -xzf repo.tar.gz
cd git-repo-main
```

### 步骤 2: 检查项目结构

repo 项目包含：
- `repo` - launcher 启动脚本（约 45KB）
- `main.py` - 主入口程序
- `*.py` - Python 模块文件（约 20 个）
- `subcmds/` - 子命令模块目录
- `hooks/` - Git hooks 脚本

### 步骤 3: 创建 staging 安装目录

```bash
mkdir -p ~/tmp/test-install-repo-2/$HOME/usr/local/bin
mkdir -p ~/tmp/test-install-repo-2/$HOME/usr/local/lib/repo
cp repo ~/tmp/test-install-repo-2/$HOME/usr/local/bin/
cp *.py ~/tmp/test-install-repo-2/$HOME/usr/local/lib/repo/
cp -r subcmds ~/tmp/test-install-repo-2/$HOME/usr/local/lib/repo/
cp -r hooks ~/tmp/test-install-repo-2/$HOME/usr/local/lib/repo/
```

### 步骤 4: 创建预编译包

```bash
cd ~/tmp/test-install-repo-2/storage/Users/currentUser/usr/local
tar -czvf repo-2-ohos-aarch64.tar.gz bin lib
```

**包大小**: 918KB

## 依赖分析

### 必需依赖
- **git**: repo 是 Git 的包装工具，需要 git 命令
- **python**: 运行 Python 脚本，需要 >= 3.6

### 可选依赖
- 无

## 鸿蒙适配

### 平台兼容性
repo 是纯 Python 脚本，理论上在任何有 Python 的平台都能运行。鸿蒙平台需要：
- Python 3.x 环境
- git 命令可用

### 特殊处理
- 无需 ELF 筋名（非二进制文件）
- 无需 RPATH 设置
- 无需 configure/make 步骤

## 使用说明

### 标准方式（推荐）
```bash
# 安装 launcher 脚本
tar -xzf repo-2-ohos-aarch64.tar.gz -C $HOME/usr/local

# 添加到 PATH
export PATH=$HOME/usr/local/bin:$PATH

# 首次运行会自动下载完整 repo 工具
repo init -u <manifest-url>
```

### 环境变量配置
- `REPO_URL`: 指定 repo 仓库 URL
- `REPO_REV`: 指定 repo 分支/版本
- `REPO_TRACE`: 启用调试跟踪

## 验证测试

### 功能验证
```bash
# 检查版本
repo --version

# 查看帮助
repo help
```

### 注意事项
1. repo 第一次运行时会从网络下载完整的工具到 `.repo/repo/` 目录
2. 需要网络访问 gerrit.googlesource.com
3. 如网络受限，可通过 REPO_URL 环境变量使用镜像源

## 编译结束

**编译时间**: 2026-06-04 22:01
**最终状态**: built
**产物路径**: archives/r/repo/2/packaging/repo-2-ohos-aarch64.tar.gz
**补丁数量**: 0
**质量门禁**: N/A（纯 Python 项目）