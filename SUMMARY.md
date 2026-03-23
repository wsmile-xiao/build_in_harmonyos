# 鸿蒙平台开源软件编译兼容性总览

> 最后更新：2026-03-24
> 已收录软件：26 款 / 27 个版本

## 📊 总体统计

| 指标 | 数量 |
|------|------|
| 收录软件 | **26** 款 |
| 软件版本 | **27** 个 |
| ✅ 完全成功 | 18 |
| ⚠️ 部分成功 | 8 |
| ❌ 编译失败 | 0 |

| 构建系统 | 数量 |
|----------|------|
| Autotools | 23 |
| CMake | 1 |
| Makefile | 1 |
| Custom Perl | 1 |
| Script | 1 |

## 📋 软件兼容性一览

| 软件 | 版本 | 状态 | 兼容性 | 构建系统 | 补丁数 | 依赖 | 详情 |
|------|------|------|--------|----------|--------|------|------|
| **automake** | 1.16.5 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | autoconf,perl | [📄](archives/a/automake/1.16.5/) |
| **bash** | 5.3 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | ncurses,readline | [📄](archives/b/bash/5.3/) |
| **bzip2** | 1.0.8 | ✅ 完全成功 | 🟢 高 | Makefile | 1 | - | [📄](archives/b/bzip2/1.0.8/) |
| **coreutils** | 9.10 | ⚠️ 部分成功 | 🟡 中 | Autotools | 3 | gmp,libcap,selinux | [📄](archives/c/coreutils/9.10/) |
| **file** | 5.45 | ✅ 完全成功 | 未评估 | Autotools | 0 | - | [📄](archives/f/file/5.45/) |
| **gawk** | 5.3.0 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | mpfr,gmp | [📄](archives/g/gawk/5.3.0/) |
| **gdbm** | 1.23 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | readline | [📄](archives/g/gdbm/1.23/) |
| **help2man** | 1.49.3 | ✅ 完全成功 | 未评估 | Script | 0 | - | [📄](archives/h/help2man/1.49.3/) |
| **htop** | 3.4.1 | ⚠️ 部分成功 | 未评估 | Autotools | 0 | - | [📄](archives/h/htop/3.4.1/) |
| **jq** | 1.7.1 | ✅ 完全成功 | 🟢 高 | Autotools | 2 | oniguruma | [📄](archives/j/jq/1.7.1/) |
| **libffi** | 3.4.4、3.5.2 | ✅ 完全成功 | 未评估 | Autotools | 0 | - | [📄](archives/l/libffi/3.5.2/) |
| **libpipeline** | 1.5.8 | ✅ 完全成功 | 🟢 高 | Autotools | 2 | libgio | [📄](archives/l/libpipeline/1.5.8/) |
| **libtool** | 2.4.7 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | automake,autoconf | [📄](archives/l/libtool/2.4.7/) |
| **lzma** | 5.6.2 | ✅ 完全成功 | 未评估 | Autotools | 0 | - | [📄](archives/l/lzma/5.6.2/) |
| **man-db** | 2.13.1 | ✅ 完全成功 | 🟡 中 | Autotools | 5 | gdbm 1.23,bzip2 1.0.8,libpipeline 1.5.8,groff 1.23.0 | [📄](archives/m/man-db/2.13.1/) |
| **ncurses** | 6.4 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | - | [📄](archives/n/ncurses/6.4/) |
| **openssl** | 1.1.1w | ✅ 完全成功 | 🟢 高 | Custom Perl | 1 | perl；zlib | [📄](archives/o/openssl/1.1.1w/) |
| **patch** | 2.7.6 | ⚠️ 部分成功 | 未评估 | Autotools | 0 | - | [📄](archives/p/patch/2.7.6/) |
| **python** | 3.9.0 | ⚠️ 部分成功 | 🟡 中 | Autotools | 3 | zlib,openssl,ncurses... | [📄](archives/p/python/3.9.0/) |
| **readline** | 8.2 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | ncurses | [📄](archives/r/readline/8.2/) |
| **rsync** | 3.3.0 | ⚠️ 部分成功 | 未评估 | Autotools | 0 | - | [📄](archives/r/rsync/3.3.0/) |
| **sed** | 4.9 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | selinux | [📄](archives/s/sed/4.9/) |
| **strace** | 6.19 | ⚠️ 部分成功 | 🔴 低 | Autotools | 3 | - | [📄](archives/s/strace/6.19/) |
| **tar** | 1.35 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | - | [📄](archives/t/tar/1.35/) |
| **wget** | 1.19.1 | ⚠️ 部分成功 | 未评估 | Autotools | 0 | - | [📄](archives/w/wget/1.19.1/) |
| **zlib** | 1.3.1 | ✅ 完全成功 | 🟢 高 | CMake | 0 | - | [📄](archives/z/zlib/1.3.1/) |

---

## 📖 各软件详细信息

以下按字母顺序列出每个软件的完整编译信息，包括兼容性评估、
已知问题、适配补丁列表和报告链接。

### automake 1.16.5

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 🟢 高 |
| **构建系统** | Autotools |
| **编译日期** | 2024-03-19 |
| **目标三元组** | `aarch64-unknown-linux-ohos` |
| **依赖** | 必需：autoconf、perl |
| **补丁数量** | 1 个 |
| **测试结果** | **manual**：无测试 |

#### ⚠️ 已知问题

无

- 编译 autotools 项目必需

#### 📝 适配补丁

| # | 补丁 | 说明 |
|---|------|------|
| 01 | [`0001-port-for-ohos.patch`](archives/a/automake/1.16.5/0001-port-for-ohos.patch) | 添加 HarmonyOS 系统检测 |

#### 📄 详细报告

- [编译说明](archives/a/automake/1.16.5/README.md)
- [测试报告](archives/a/automake/1.16.5/reports/test-report.md)

### bash 5.3

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 🟢 高 |
| **构建系统** | Autotools |
| **编译日期** | 2024-03-17 |
| **目标三元组** | `aarch64-unknown-linux-ohos` |
| **依赖** | 可选：ncurses、readline |
| **补丁数量** | 1 个 |
| **测试结果** | **manual**：无测试 |

#### ⚠️ 已知问题

无

- 完全可用

#### 📝 适配补丁

| # | 补丁 | 说明 |
|---|------|------|
| 01 | [`0001-port-for-ohos.patch`](archives/b/bash/5.3/0001-port-for-ohos.patch) | 添加 HarmonyOS 系统检测 |

#### 📄 详细报告

- [编译说明](archives/b/bash/5.3/README.md)
- [测试报告](archives/b/bash/5.3/reports/test-report.md)

### bzip2 1.0.8

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 🟢 高 |
| **构建系统** | Makefile |
| **编译日期** | 2024-03-20 |
| **目标三元组** | `未指定` |
| **补丁数量** | 1 个 |
| **测试结果** | **manual**：无测试 |

#### ⚠️ 已知问题

无

- 需要修改 Makefile 添加 -fPIC

#### 📝 适配补丁

| # | 补丁 | 说明 |
|---|------|------|
| 01 | [`0001-makefile-fpic.patch`](archives/b/bzip2/1.0.8/0001-makefile-fpic.patch) | 添加 -fPIC 编译标志 |

#### 📄 详细报告

- [编译说明](archives/b/bzip2/1.0.8/README.md)
- [测试报告](archives/b/bzip2/1.0.8/reports/test-report.md)

### coreutils 9.10

| 属性 | 值 |
|------|-----|
| **状态** | ⚠️ 部分成功 |
| **兼容性** | 🟡 中 |
| **构建系统** | Autotools |
| **编译日期** | 2024-03-19 |
| **目标三元组** | `aarch64-unknown-linux-ohos` |
| **依赖** | 可选：gmp、libcap、selinux |
| **补丁数量** | 3 个 |
| **测试结果** | **manual**：无测试 |

**已验证的关键功能**：cat, head, tail、grep, sed, awk、chmod, chown（非软链接）、touch, mkdir, rmdir

#### ⚠️ 已知问题

- SELinux 限制软链接访问
- 部分命令（ls, rm, cp）无法处理软链接
- toybox 命令可以正常处理软链接

- 大部分命令正常工作
- 涉及软链接操作的命令需要使用 toybox 版本
- 建议设置别名使用 toybox 的 ls, rm, cp, mv

#### 📝 适配补丁

| # | 补丁 | 说明 |
|---|------|------|
| 01 | [`0001-port-for-ohos.patch`](archives/c/coreutils/9.10/0001-port-for-ohos.patch) | 添加 HarmonyOS 系统检测支持 |
| 02 | [`0002-fix-fstat-for-harmonyos.patch`](archives/c/coreutils/9.10/0002-fix-fstat-for-harmonyos.patch) | 修复 fstat 对管道/终端返回 EACCES 的问题 |
| 03 | [`0003-fix-musl-compat.patch`](archives/c/coreutils/9.10/0003-fix-musl-compat.patch) | musl libc 兼容性修复（FILE 结构体差异） |

#### 📄 详细报告

- [编译说明](archives/c/coreutils/9.10/README.md)
- [测试报告](archives/c/coreutils/9.10/reports/test-report.md)

### file 5.45

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 未评估 |
| **构建系统** | Autotools |
| **编译日期** | 未知 |
| **目标三元组** | `未指定` |
| **补丁数量** | 0 个 |
| **测试结果** | 未测试 |

#### 📄 详细报告

- [编译说明](archives/f/file/5.45/README.md)
- [测试报告](archives/f/file/5.45/reports/test-report.md)

### gawk 5.3.0

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 🟢 高 |
| **构建系统** | Autotools |
| **编译日期** | 2024-03-18 |
| **目标三元组** | `aarch64-unknown-linux-ohos` |
| **依赖** | 可选：mpfr、gmp |
| **补丁数量** | 1 个 |
| **测试结果** | **manual**：无测试 |

#### ⚠️ 已知问题

无

- 替代 toybox awk

#### 📝 适配补丁

| # | 补丁 | 说明 |
|---|------|------|
| 01 | [`0001-port-for-ohos.patch`](archives/g/gawk/5.3.0/0001-port-for-ohos.patch) | 添加 HarmonyOS 系统检测 |

#### 📄 详细报告

- [编译说明](archives/g/gawk/5.3.0/README.md)
- [测试报告](archives/g/gawk/5.3.0/reports/test-report.md)

### gdbm 1.23

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 🟢 高 |
| **构建系统** | Autotools |
| **编译日期** | 2024-03-21 |
| **目标三元组** | `aarch64-unknown-linux-ohos` |
| **依赖** | 可选：readline |
| **补丁数量** | 1 个 |
| **测试结果** | **manual**：无测试 |

#### ⚠️ 已知问题

无

- Python gdbm 模块依赖

#### 📝 适配补丁

| # | 补丁 | 说明 |
|---|------|------|
| 01 | [`0001-port-for-ohos.patch`](archives/g/gdbm/1.23/0001-port-for-ohos.patch) | 添加 HarmonyOS 系统检测 |

#### 📄 详细报告

- [编译说明](archives/g/gdbm/1.23/README.md)
- [测试报告](archives/g/gdbm/1.23/reports/test-report.md)

### help2man 1.49.3

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 未评估 |
| **构建系统** | Script |
| **编译日期** | 未知 |
| **目标三元组** | `未指定` |
| **补丁数量** | 0 个 |
| **测试结果** | 未测试 |

#### 📄 详细报告

- [编译说明](archives/h/help2man/1.49.3/README.md)
- [测试报告](archives/h/help2man/1.49.3/reports/test-report.md)

### htop 3.4.1

| 属性 | 值 |
|------|-----|
| **状态** | ⚠️ 部分成功 |
| **兼容性** | 未评估 |
| **构建系统** | Autotools |
| **编译日期** | 未知 |
| **目标三元组** | `未指定` |
| **补丁数量** | 0 个 |
| **测试结果** | 未测试 |

#### 📄 详细报告

- [编译说明](archives/h/htop/3.4.1/README.md)
- [测试报告](archives/h/htop/3.4.1/reports/test-report.md)

### jq 1.7.1

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 🟢 高 |
| **构建系统** | Autotools |
| **编译日期** | 2026-03-22 |
| **目标三元组** | `aarch64-unknown-linux-ohos` |
| **依赖** | 可选：oniguruma |
| **补丁数量** | 2 个 |
| **测试结果** | **official**：5/6 通过（83%），1 失败 |

#### ⚠️ 已知问题

无

- 核心功能正常
- 未启用 oniguruma（正则表达式支持）
- 可选：编译 oniguruma 后重新编译 jq 获得完整功能

#### 📝 适配补丁

| # | 补丁 | 说明 |
|---|------|------|
| 01 | [`0001-config-guess-harmonyos-support.patch`](archives/j/jq/1.7.1/patches/0001-config-guess-harmonyos-support.patch) | 添加 HarmonyOS 平台识别到 config.guess |
| 02 | [`0002-config-sub-harmonyos-support.patch`](archives/j/jq/1.7.1/patches/0002-config-sub-harmonyos-support.patch) | 添加 linux-ohos 三元组支持到 config.sub |

#### 📄 详细报告

- [编译说明](archives/j/jq/1.7.1/README.md)
- [测试报告](archives/j/jq/1.7.1/reports/test-report.md)

### libffi 3.4.4

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 🟢 高 |
| **构建系统** | Autotools |
| **编译日期** | 2024-03-12 |
| **目标三元组** | `aarch64-unknown-linux-ohos` |
| **补丁数量** | 1 个 |
| **测试结果** | **skipped**：无测试 |

**已验证的关键功能**：ffi_call、ffi_closure

#### ⚠️ 已知问题

无

- FFI 核心功能完全可用
- 多架构支持（aarch64, arm, x86_64）
- 动态库和静态库正常

#### 📝 适配补丁

| # | 补丁 | 说明 |
|---|------|------|
| 01 | [`0001-port-for-ohos.patch`](archives/l/libffi/3.4.4/0001-port-for-ohos.patch) | 修改 config.guess 和 config.sub 支持 HarmonyOS |

#### 📄 详细报告

- [编译说明](archives/l/libffi/3.4.4/README.md)
- [测试报告](archives/l/libffi/3.4.4/reports/test-report.md)

### libffi 3.5.2

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 未评估 |
| **构建系统** | Autotools |
| **编译日期** | 未知 |
| **目标三元组** | `未指定` |
| **补丁数量** | 0 个 |
| **测试结果** | 未测试 |

#### 📄 详细报告

- [编译说明](archives/l/libffi/3.5.2/README.md)
- [测试报告](archives/l/libffi/3.5.2/reports/test-report.md)

### libpipeline 1.5.8

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 🟢 高 |
| **构建系统** | Autotools |
| **编译日期** | 2026-03-23 |
| **目标三元组** | `aarch64-unknown-linux-ohos` |
| **依赖** | 可选：libgio |
| **补丁数量** | 2 个 |
| **测试结果** | **indirect**：无测试 |

#### ⚠️ 已知问题

无

- man-db 的核心依赖

#### 📝 适配补丁

| # | 补丁 | 说明 |
|---|------|------|
| 01 | [`0001-config.guess-add-HarmonyOS-detection.patch`](archives/l/libpipeline/1.5.8/0001-config.guess-add-HarmonyOS-detection.patch) | config.guess 添加 __OHOS__ LIBC 检测和 HarmonyOS case，返回 aarch64-unknown-linux-ohos |
| 02 | [`0002-config.sub-add-linux-ohos-support.patch`](archives/l/libpipeline/1.5.8/0002-config.sub-add-linux-ohos-support.patch) | config.sub 添加 ohos-linux 匹配、OS 允许列表 ohos*、kernel-os 验证 linux-ohos* |

#### 📄 详细报告

- [编译说明](archives/l/libpipeline/1.5.8/README.md)
- [测试报告](archives/l/libpipeline/1.5.8/reports/test-report.md)

### libtool 2.4.7

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 🟢 高 |
| **构建系统** | Autotools |
| **编译日期** | 2024-03-19 |
| **目标三元组** | `aarch64-unknown-linux-ohos` |
| **依赖** | 必需：automake、autoconf |
| **补丁数量** | 1 个 |
| **测试结果** | **manual**：无测试 |

#### ⚠️ 已知问题

- libtoolize 在 zsh 下有兼容问题

- Autotools 共享库支持必需

#### 📝 适配补丁

| # | 补丁 | 说明 |
|---|------|------|
| 01 | [`0001-port-for-ohos.patch`](archives/l/libtool/2.4.7/0001-port-for-ohos.patch) | 添加 HarmonyOS 系统检测 |

#### 📄 详细报告

- [编译说明](archives/l/libtool/2.4.7/README.md)
- [测试报告](archives/l/libtool/2.4.7/reports/test-report.md)

### lzma 5.6.2

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 未评估 |
| **构建系统** | Autotools |
| **编译日期** | 未知 |
| **目标三元组** | `未指定` |
| **补丁数量** | 0 个 |
| **测试结果** | 未测试 |

#### 📄 详细报告

- [编译说明](archives/l/lzma/5.6.2/README.md)
- [测试报告](archives/l/lzma/5.6.2/reports/test-report.md)

### man-db 2.13.1

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 🟡 中 |
| **构建系统** | Autotools |
| **编译日期** | 2026-03-23 |
| **目标三元组** | `aarch64-unknown-linux-ohos` |
| **依赖** | 必需：gdbm 1.23、bzip2 1.0.8、libpipeline 1.5.8、groff 1.23.0 |
| **补丁数量** | 5 个 |
| **测试结果** | **manual**：无测试 |

#### ⚠️ 已知问题

- musl libc iconv 不支持 //IGNORE 后缀，导致 manconv whatis parse 失败，apropos/whatis 不可用

- man page 显示功能正常，带 ANSI 颜色格式化
- mandb 初始化可运行但 whatis 数据库不完整

#### 📝 适配补丁

| # | 补丁 | 说明 |
|---|------|------|
| 01 | [`0001-config.sub-add-linux-ohos-support.patch`](archives/m/man-db/2.13.1/0001-config.sub-add-linux-ohos-support.patch) | config.sub 添加 ohos-linux 匹配和 OS 允许列表（上游 config.guess 已自带 HarmonyOS 检测，但 config.sub 缺少 ohos 支持） |
| 02 | [`0002-security.c-handle-missing-man-owner.patch`](archives/m/man-db/2.13.1/0002-security.c-handle-missing-man-owner.patch) | lib/security.c 中 get_man_owner() 找不到 man 用户时 debug 警告并返回 NULL，而非 error(FAIL) 退出 |
| 03 | [`0003-encodings.c-replace-locale-device-with-utf8.patch`](archives/m/man-db/2.13.1/0003-encodings.c-replace-locale-device-with-utf8.patch) | lib/encodings.c 中 charset_table 的 "locale" 设备改为 "utf8"，适配 groff 1.23.0（无 devlocale） |
| 04 | [`0004-man.c-replace-locale-roff-device-with-utf8.patch`](archives/m/man-db/2.13.1/0004-man.c-replace-locale-roff-device-with-utf8.patch) | src/man.c 中 HEIRLOOM_NROFF 分支 roff_device 从 "locale" 改为 "utf8"，适配 groff 1.23.0 |
| 05 | [`(构建时修改) config.h 中`](archives/m/man-db/2.13.1/(构建时修改) config.h 中) | 避免整个权限相关代码被编译（更彻底的方案，使 get_man_owner() 不被编译） |

#### 📄 详细报告

- [编译说明](archives/m/man-db/2.13.1/README.md)
- [测试报告](archives/m/man-db/2.13.1/reports/test-report.md)

### ncurses 6.4

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 🟢 高 |
| **构建系统** | Autotools |
| **编译日期** | 2024-03-15 |
| **目标三元组** | `aarch64-unknown-linux-ohos` |
| **补丁数量** | 1 个 |
| **测试结果** | **manual**：无测试 |

#### ⚠️ 已知问题

无

- 使用 --enable-overwrite 让头文件安装到顶层
- readline 依赖 ncurses

#### 📝 适配补丁

| # | 补丁 | 说明 |
|---|------|------|
| 01 | [`0001-port-for-ohos.patch`](archives/n/ncurses/6.4/0001-port-for-ohos.patch) | 添加 HarmonyOS 系统检测 |

#### 📄 详细报告

- [编译说明](archives/n/ncurses/6.4/README.md)
- [测试报告](archives/n/ncurses/6.4/reports/test-report.md)

### openssl 1.1.1w

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 🟢 高 |
| **构建系统** | Custom Perl |
| **编译日期** | 2024-03-21 |
| **目标三元组** | `openharmony-aarch64` |
| **依赖** | 必需：perl；可选：zlib |
| **补丁数量** | 1 个 |
| **测试结果** | **manual**：29/35 通过（83%），6 失败 |

**已验证的关键功能**：AES 加密、RSA 密钥生成、TLS 1.3 连接、HTTPS 客户端

#### ⚠️ 已知问题

无

- 核心加密功能完全可用
- 使用 no-asm 禁用汇编优化（避免 BAD_SIGNATURE bug）
- TLS 1.3 正常工作

#### 📝 适配补丁

| # | 补丁 | 说明 |
|---|------|------|
| 01 | [`0001-support-build-in-harmonyos.patch`](archives/o/openssl/1.1.1w/0001-support-build-in-harmonyos.patch) | 添加 HarmonyOS 平台配置和自动检测 |

#### 📄 详细报告

- [编译说明](archives/o/openssl/1.1.1w/README.md)
- [测试报告](archives/o/openssl/1.1.1w/reports/test-report.md)

### patch 2.7.6

| 属性 | 值 |
|------|-----|
| **状态** | ⚠️ 部分成功 |
| **兼容性** | 未评估 |
| **构建系统** | Autotools |
| **编译日期** | 未知 |
| **目标三元组** | `未指定` |
| **补丁数量** | 0 个 |
| **测试结果** | 未测试 |

#### 📄 详细报告

- [编译说明](archives/p/patch/2.7.6/README.md)
- [测试报告](archives/p/patch/2.7.6/reports/test-report.md)

### python 3.9.0

| 属性 | 值 |
|------|-----|
| **状态** | ⚠️ 部分成功 |
| **兼容性** | 🟡 中 |
| **构建系统** | Autotools |
| **编译日期** | 2024-03-20 |
| **目标三元组** | `aarch64-unknown-linux-ohos` |
| **依赖** | 可选：zlib、openssl、ncurses、readline、gdbm |
| **补丁数量** | 3 个 |
| **测试结果** | **manual**：350/400 通过（88%），50 失败 |

**已验证的关键功能**：基本语法、文件操作、网络编程、多线程、SSL/HTTPS（需要 OpenSSL）

#### ⚠️ 已知问题

- 扩展模块需要特殊处理（musl BIND_NOW）
- 部分 C 加速模块需要手动编译
- PTY 功能不可用（系统限制）

- 主程序正常工作
- 60 个扩展模块中约 40 个可用
- _ssl 模块需要手动链接 libssl
- subprocess 需要使用管道语法

#### 📝 适配补丁

| # | 补丁 | 说明 |
|---|------|------|
| 01 | [`0001-configure-ac-harmonyos-support.patch`](archives/p/python/3.9.0/patches/0001-configure-ac-harmonyos-support.patch) | 添加 HarmonyOS 平台检测和配置 |
| 02 | [`0002-Lib-sysconfig-py-platform-string-fix.patch`](archives/p/python/3.9.0/patches/0002-Lib-sysconfig-py-platform-string-fix.patch) | 修复平台字符串包含空格的问题 |
| 03 | [`0003-subprocess-pipe-workaround.patch`](archives/p/python/3.9.0/patches/0003-subprocess-pipe-workaround.patch) | 使用管道语法绕过 SELinux 域转换限制 |

#### 📄 详细报告

- [编译说明](archives/p/python/3.9.0/README.md)
- [测试报告](archives/p/python/3.9.0/reports/test-report.md)

### readline 8.2

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 🟢 高 |
| **构建系统** | Autotools |
| **编译日期** | 2024-03-16 |
| **目标三元组** | `aarch64-unknown-linux-ohos` |
| **依赖** | 必需：ncurses |
| **补丁数量** | 1 个 |
| **测试结果** | **manual**：无测试 |

#### ⚠️ 已知问题

无

- bash 依赖 readline

#### 📝 适配补丁

| # | 补丁 | 说明 |
|---|------|------|
| 01 | [`0001-port-for-ohos.patch`](archives/r/readline/8.2/0001-port-for-ohos.patch) | 添加 HarmonyOS 系统检测 |

#### 📄 详细报告

- [编译说明](archives/r/readline/8.2/README.md)
- [测试报告](archives/r/readline/8.2/reports/test-report.md)

### rsync 3.3.0

| 属性 | 值 |
|------|-----|
| **状态** | None |
| **兼容性** | 未评估 |
| **构建系统** | None |
| **编译日期** | 未知 |
| **目标三元组** | `未指定` |
| **补丁数量** | 0 个 |
| **测试结果** | 未测试 |

#### 📄 详细报告

- [编译说明](archives/r/rsync/3.3.0/README.md)
- [测试报告](archives/r/rsync/3.3.0/reports/test-report.md)

### sed 4.9

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 🟢 高 |
| **构建系统** | Autotools |
| **编译日期** | 2024-03-17 |
| **目标三元组** | `aarch64-unknown-linux-ohos` |
| **依赖** | 可选：selinux |
| **补丁数量** | 1 个 |
| **测试结果** | **manual**：无测试 |

#### ⚠️ 已知问题

无

- 完全替代 toybox sed，支持所有 GNU sed 特性

#### 📝 适配补丁

| # | 补丁 | 说明 |
|---|------|------|
| 01 | [`0001-port-for-ohos.patch`](archives/s/sed/4.9/0001-port-for-ohos.patch) | 添加 HarmonyOS 系统检测支持 |

#### 📄 详细报告

- [编译说明](archives/s/sed/4.9/README.md)
- [测试报告](archives/s/sed/4.9/reports/test-report.md)

### strace 6.19

| 属性 | 值 |
|------|-----|
| **状态** | ⚠️ 部分成功 |
| **兼容性** | 🔴 低 |
| **构建系统** | Autotools |
| **编译日期** | 2026-03-23 |
| **目标三元组** | `aarch64-unknown-linux-ohos` |
| **补丁数量** | 3 个 |
| **测试结果** | **manual**：1/2 通过（50%），1 失败 |

#### ⚠️ 已知问题

- ptrace 系统调用被 SELinux 策略禁止（adhoc_bin 域），strace 无法执行实际追踪

- 编译产物正确，但 SELinux 限制了 ptrace 权限，核心功能不可用

#### 📝 适配补丁

| # | 补丁 | 说明 |
|---|------|------|
| 01 | [`0001-add-harmonyos-support-to-config.sub.patch`](archives/s/strace/6.19/0001-add-harmonyos-support-to-config.sub.patch) | 在 config.sub 中添加 ohos-linux 三元组支持和 linux-ohos 内核-OS 组合验证 |
| 02 | [`0002-fix-unused-function-warning-in-sigreturn.patch`](archives/s/strace/6.19/0002-fix-unused-function-warning-in-sigreturn.patch) | 修复 sigreturn.c 中 print_sigmask_addr_size 未使用函数的编译错误（clang -Werror） |
| 03 | [`0003-add-harmonyos-support-to-config.guess.patch`](archives/s/strace/6.19/0003-add-harmonyos-support-to-config.guess.patch) | 在 config.guess 中添加 HarmonyOS 系统识别（case 匹配、LIBC=ohos 检测、GUESS 三元组输出） |

#### 📄 详细报告

- [编译说明](archives/s/strace/6.19/README.md)
- [测试报告](archives/s/strace/6.19/reports/test-report.md)
- [编译报告](archives/s/strace/6.19/reports/build-report.md)

### tar 1.35

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 🟢 高 |
| **构建系统** | Autotools |
| **编译日期** | 2024-03-18 |
| **目标三元组** | `aarch64-unknown-linux-ohos` |
| **补丁数量** | 1 个 |
| **测试结果** | **manual**：无测试 |

#### ⚠️ 已知问题

无

- 替代 toybox tar，支持更多格式

#### 📝 适配补丁

| # | 补丁 | 说明 |
|---|------|------|
| 01 | [`0001-port-for-ohos.patch`](archives/t/tar/1.35/0001-port-for-ohos.patch) | 添加 HarmonyOS 系统检测 |

#### 📄 详细报告

- [编译说明](archives/t/tar/1.35/README.md)
- [测试报告](archives/t/tar/1.35/reports/test-report.md)

### wget 1.19.1

| 属性 | 值 |
|------|-----|
| **状态** | ⚠️ 部分成功 |
| **兼容性** | 未评估 |
| **构建系统** | Autotools |
| **编译日期** | 未知 |
| **目标三元组** | `未指定` |
| **补丁数量** | 0 个 |
| **测试结果** | 未测试 |

#### 📄 详细报告

- [编译说明](archives/w/wget/1.19.1/README.md)
- [测试报告](archives/w/wget/1.19.1/reports/test-report.md)

### zlib 1.3.1

| 属性 | 值 |
|------|-----|
| **状态** | ✅ 完全成功 |
| **兼容性** | 🟢 高 |
| **构建系统** | CMake |
| **编译日期** | 2024-03-20 |
| **目标三元组** | `未指定` |
| **补丁数量** | 0 个 |
| **测试结果** | **manual**：无测试 |

#### ⚠️ 已知问题

无

- 编译简单，无兼容性问题

#### 📄 详细报告

- [编译说明](archives/z/zlib/1.3.1/README.md)
- [测试报告](archives/z/zlib/1.3.1/reports/test-report.md)

---

*本文档由 `scripts/gen_summary.py` 从编译档案自动生成，请勿手动编辑。*

Copyright (c) 2024-2026 OpenHarmony PC Developer社区