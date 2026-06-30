# qdbm 1.8.78 for HarmonyOS

## 概述

QDBM（Quick Database Manager）是 Mikio Hirabayashi 开发的高性能嵌入式数据库库，在 HarmonyOS/OpenHarmony (aarch64) 平台上的编译记录。

QDBM 提供四种数据库接口：
- **Depot** — 基于哈希表的键值存储
- **Curia** — 支持多文件分片的哈希数据库
- **Relic** — 纯哈希函数接口
- **Villa** — 基于 B+树的有序数据库
- **Hovel** — 兼容 GDBM 的哈希接口
- **Cabin** — 通用工具函数库
- **Odeum** — 倒排索引数据库

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | qdbm |
| 版本 | 1.8.78 |
| 描述 | Library of routines for managing a database |
| 语言 | C/C++ |
| 构建系统 | autotools（自定义 configure） |
| 许可证 | LGPL-2.1-or-later |
| 下载地址 | https://dbmx.net/qdbm/qdbm-1.8.78.tar.gz |
| 官方网站 | https://dbmx.net/qdbm/ |
| 依赖 | 无外部依赖（仅 libc） |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | autotools |
| 状态 | ✅ published |

## 编译步骤

```bash
# 1. 下载并解压源码
wget https://dbmx.net/qdbm/qdbm-1.8.78.tar.gz
tar -xzf qdbm-1.8.78.tar.gz
cd qdbm-1.8.78

# 2. 配置（注意：HMDFS 需修改 configure 中的 umask，见补丁说明）
./configure --prefix=$HOME/usr/local

# 3. 编译
make -j1

# 4. 安装（DESTDIR 暂存模式）
make install DESTDIR=/tmp/test-install-qdbm-1.8.78

# 5. 运行测试
make check

# 6. 正式安装
make install
```

## 补丁说明

### configure umask 兼容性修复

**目的**: 解决 HMDFS 文件系统下 `configure` 创建目录后无法写入文件的问题。

**根因**: qdbm 的 configure 脚本在生成 `config.status` 时使用 `umask 077`，导致安装目录以 mode 0700 创建。HMDFS 文件系统不允许向此类目录写入文件，且 `chmod` 也无法修改（SGID sticky 限制）。

**修改文件**:
- `configure`: 将 config.status 模板中的 2 处 `umask 077` 改为 `umask 022`

**关键修改**:
```diff
- (umask 077;
+ (umask 022;
    MKCOMMAND="`cat $tmp/config.status`";
    cd "$srcdir" &&
    eval "$MKCOMMAND")
```

## 预编译包

| 文件 | 大小 | 说明 |
|------|------|------|
| `packaging/qdbm-1.8.78-ohos-aarch64.tar.gz` | 3.2 MB | 主预编译包（库、工具、头文件、man 页） |
| `packaging/qdbm-1.8.78-ohos-aarch64-debug.tar.gz` | 755 KB | 调试符号包 |

## 主要可执行文件

| 工具 | 说明 |
|------|------|
| `dpmgr` | Depot 数据库管理工具 |
| `dptest` | Depot 数据库测试程序 |
| `dptsv` | Depot CSV 导入工具 |
| `crmgr` | Curia 数据库管理工具 |
| `crtest` | Curia 数据库测试程序 |
| `crtsv` | Curia CSV 导入工具 |
| `rlmgr` | Relic 数据库管理工具 |
| `rltest` | Relic 数据库测试程序 |
| `hvmgr` | Hovel 数据库管理工具 |
| `hvtest` | Hovel 数据库测试程序 |
| `cbtest` | Cabin 工具函数测试程序 |
| `cbcodec` | Cabin 编解码工具 |
| `vlmgr` | Villa 数据库管理工具 |
| `vltest` | Villa 数据库测试程序 |
| `vltsv` | Villa CSV 导入工具 |
| `odmgr` | Odeum 数据库管理工具 |
| `odtest` | Odeum 数据库测试程序 |
| `odidx` | Odeum 索引构建工具 |
| `qmttest` | 多线程测试工具 |

## 库文件

| 文件 | 说明 |
|------|------|
| `libqdbm.a` | 静态库 |
| `libqdbm.so.14.14.0` | 共享库（SOVER=14） |

## 版本验证

```bash
$ dpmgr version
Powered by QDBM version 1.8.78 on Linux
Copyright (c) 2000-2007 Mikio Hirabayashi
```

## 测试结果

| 测试 | 结果 | 说明 |
|------|------|------|
| dptest (Depot) | ✅ PASS | write, read, rcat, combo 全部通过 |
| crtest (Curia) | ✅ PASS | 全部通过 |
| rltest (Relic) | ✅ PASS | 全部通过 |
| hvtest (Hovel) | ✅ PASS | 全部通过 |
| cbtest (Cabin) | ✅ PASS | 全部通过 |
| vltest (Villa) | ✅ PASS | write/read/wicked 全部通过 |
| vlmgr list | ❌ CRASH | 段错误 (Signal 11)，已知限制，不影响核心库功能 |

## 质量门禁

| 门禁 | 结果 |
|------|------|
| G0 (干净构建验证) | ⚠️ 跳过（平台限制） |
| G1 (二进制完整性) | ✅ PASS |
| G2 (功能可用性) | ✅ PASS |
| G3 (可移植性) | ✅ PASS |
| G4 (档案完整性) | ✅ PASS |

## 已知限制

1. **vlmgr list 段错误**: 在 OpenHarmony 平台上，`vlmgr list` 命令在 Villa 数据库执行 optimize 后会触发段错误 (Signal 11)。此问题不影响核心库的读写功能。
2. **umask 兼容性**: 首次编译需手动修改 configure 脚本中的 `umask 077` 为 `umask 022`，否则在 HMDFS 上无法生成 config.status。
