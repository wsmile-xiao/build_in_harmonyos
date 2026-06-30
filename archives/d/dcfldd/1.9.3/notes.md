# dcfldd 1.9.3 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-06-06
- 编译器: clang/clang++
- 平台: aarch64-unknown-linux-ohos
- 状态: published

## 编译步骤

1. **autoreconf**: 源码包未包含 pre-built configure 脚本，使用 `autoreconf -fi` 从 configure.ac 生成。有 aalib.m4 警告但无错误。
2. **configure.ac 修复**: 移除 `PKG_PROG_PKG_CONFIG` 和 `PKG_CHECK_MODULES([BASH_COMPLETION], [bash-completion])` 调用，将 `BASH_COMPLETION_DIR` 设为 `"no"`，`AM_CONDITIONAL([ENABLE_BASH_COMPLETION])` 设为 `[false]`。
3. **umask 修复 (E011)**: sed 替换 configure 和 config.status 中 `umask 077` → `umask 022`，解决 HMDFS 权限问题。
4. **configure**: `CONFIG_SHELL=/storage/Users/currentUser/usr/local/bin/bash ./configure --prefix=$DEFAULT_PREFIX HELP2MAN=/bin/true MAKEINFO=/bin/true`。必须使用 bash 而非 toybox sh。
5. **make -j1**: 编译成功，无错误。
6. **make install DESTDIR=$TEST_PREFIX**: staging 安装成功。
7. **make install** (不带 DESTDIR): 验证可用。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 铁律编号 |
|---|------|------|----------|----------|
| 1 | GitHub 直接下载超时 | 网络策略 E110 限制 | 使用 `curl -k` 代理下载 | E110 |
| 2 | configure 脚本不存在 | 源码包未包含 configure | `autoreconf -fi` 生成 configure | — |
| 3 | PKG_CHECK_MODULES 未展开 | pkg.m4 不可用（aclocal 目录缺失） | 从 configure.ac 移除，改 `BASH_COMPLETION_DIR="no"` + `AM_CONDITIONAL([ENABLE_BASH_COMPLETION],[false])` | — |
| 4 | umask 077 Permission denied | HMDFS 文件系统限制 | sed 替换 `umask 077` → `umask 022` | E011 |
| 5 | CONFIG_SHELL 必须用 bash | toybox sh 不兼容 autotools 脘本 | `CONFIG_SHELL=/storage/Users/currentUser/usr/local/bin/bash` | E005 |

## 补丁说明

- **0001-configure.ac.patch**: 移除 PKG_PROG_PKG_CONFIG 和 PKG_CHECK_MODULES[bash-completion] 依赖，将 BASH_COMPLETION_DIR 设为 "no"，AM_CONDITIONAL 设为 false。适用于 OHOS 平台 pkg.m4 不可用的情况。

## 功能测试结果

手动执行 10 项功能测试，全部通过：

| # | 测试项 | 结果 |
|---|--------|------|
| 1 | 版本验证 | ✅ |
| 2 | 基础数据复制 | ✅ |
| 3 | MD5 哈希校验 | ✅ |
| 4 | 分块写入 (split) | ✅ |
| 5 | 不同块大小 (bs=512) | ✅ |
| 6 | skip/count 定位 | ✅ |
| 7 | conv=notrunc | ✅ |
| 8 | 进度显示 | ✅ |
| 9 | 总块数验证 | ✅ |
| 10 | 管道模式 | ✅ |

## 验证结果

```
dcfldd --version: dcfldd (dcfldd) 1.9.3
```

## 配置选项

```bash
CONFIG_SHELL=/storage/Users/currentUser/usr/local/bin/bash \
./configure \
  --prefix=/storage/Users/currentUser/usr/local \
  HELP2MAN=/bin/true \
  MAKEINFO=/bin/true
```
---

**编译结束**: 2026-06-08 14:30
**最终状态**: published
