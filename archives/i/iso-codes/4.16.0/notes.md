# iso-codes 4.16.0 编译笔记

## 编译信息
- 软件名称：iso-codes
- 版本：4.16.0
- 下载 URL：https://salsa.debian.org/iso-codes-team/iso-codes/-/archive/v4.16.0/iso-codes-v4.16.0.tar.bz2
- 构建系统：autotools（configure + Makefile）
- 安装前缀：~/usr/local

## 编译过程

### 问题发现（已解决）
运行 configure 时，config.status 脚本使用 `umask 077 && mktemp -d "./confXXXXXX"` 创建临时目录。
HMDFS 文件系统在 `umask 077` 下创建的目录（权限 `drwx--S---`）无法写入文件，
导致 `subs1.awk` 文件创建失败：
```
./config.status[705]: can't create ./confDpHnmh/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**根本原因**：HMDFS 文件系统对 `umask 077` 创建的目录有写入限制。SGID 位被设置，
且文件创建被拒绝。使用 `umask 022`（权限 `drwxr-sr-x`）则正常工作。

### 解决方案
修补 configure 脚本中 config.status 的临时目录创建逻辑：
1. `umask 077` → `umask 022`（HMDFS 兼容）
2. `./confXXXXXX` → `${TMPDIR:-/tmp}/confXXXXXX`（使用系统 TMPDIR）

### 编译步骤
```bash
./configure --prefix=$PREFIX
make -j2
make install DESTDIR=$DESTDIR
make check
```

### 验证结果
- configure: 通过
- make: 通过（所有 .mo 翻译文件编译成功）
- make install: 通过（703 个文件安装成功）
- make check: 通过（所有 UTF-8 验证通过）

### 安装内容
- JSON 数据文件：`share/iso-codes/json/`（8 个 ISO 标准 + 8 个 schema 文件）
- 翻译文件：`share/locale/{lang}/LC_MESSAGES/{domain}.mo`（约 680 个 .mo 文件）
- XML 文件：`share/xml/iso-codes/`（8 个 .xml 文件）
- pkg-config 文件：`share/pkgconfig/iso-codes.pc`

### 依赖
- msgfmt (GNU gettext-tools) - 可用
- msgfilter - 可用
- msgattrib - 可用
- recode-sr-latin - 可用
- msgmerge - 不可用（非必需，仅用于更新 .pot 文件）
- python3 - 可用（用于 check_valid_utf8.py 验证）

## 编译状态
- 状态：published（conan recipe 验证通过）
- 功能：完整（configure + make + make install + make check 全部通过）
- 补丁：configure umask 077 → umask 022 + TMPDIR 路径修复
---

**编译结束**: 2026-08-06 22:02
**最终状态**: built
