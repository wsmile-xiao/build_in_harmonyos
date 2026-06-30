# debianutils

## 软件描述

debianutils 是 Debian 系统特有的实用工具集合，提供了多种在 Debian 系统中常用的辅助工具。

## 版本历史

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|---------|--------|
| 5.23.2 | published | 2026-06-09 | 1 |

## 软件信息

- **官方网站**: https://salsa.debian.org/debian/debianutils
- **源码仓库**: https://deb.debian.org/debian/pool/main/d/debianutils/
- **License**: GPL-2.0-or-later
- **描述**: Miscellaneous utilities specific to Debian

## 包含工具

### 用户工具（bin）
- **run-parts**: 执行目录中的所有脚本/程序
- **tempfile**: 创建临时文件
- **ischroot**: 检测是否在 chroot 环境中运行
- **which.debianutils**: 查找命令位置（which 命令的 Debian 版本）
- **savelog**: 保存和轮转日志文件

### 系统工具（sbin）
- **installkernel**: 安装内核映像
- **add-shell**: 向 shells 列表添加 shell
- **remove-shell**: 从 shells 列表移除 shell
- **update-shells**: 更新 shells 列表

## OHOS 编译说明

### 编译配置
- 构建系统: autotools
- 编译器: clang 15.0.4
- 无特殊依赖

### 补丁说明
- **0001-Makefile.am.patch**: 禁用 po4a 文档翻译子目录（缺少 po4a-translate 工具）

### 注意事项
1. 部分工具依赖 Debian 特有功能（如 shells 文件）
2. tempfile 和 run-parts 中硬编码了 /tmp 路径（在 OHOS 上 /tmp 为只读）
3. 需要运行 autoreconf 生成 configure 脚本（源码包未预生成）