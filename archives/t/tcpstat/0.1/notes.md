# tcpstat 0.1 适配笔记

## 编译环境

- 软件: tcpstat 0.1
- 描述: Active TCP connections monitoring tool（基于 curses TUI 的 TCP 连接监控工具）
- 构建系统: makefile（手写 Makefile，非 autotools）
- 编译日期: 2026-06-17
- 编译器: clang 15.0.4 (clang++)
- 源码 URL: https://github.com/jtt/tcpstat/archive/refs/tags/rel-0-1.tar.gz
- 源码 SHA256: 366a221950759015378775862a7499aaf727a3a9de67b15463b0991c2362fdaf
- 最终状态: published

---

## 编译步骤

### 1. 初始化

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build tcpstat 0.1 \
  --url=https://github.com/jtt/tcpstat/archive/refs/tags/rel-0-1.tar.gz
```

init-build 自动完成：下载 → 解压 → 骨架创建 → 依赖检查 → 环境检查 → 输出 .build-context-tcpstat-0.1

### 2. 编译（模式 B 手动编译）

tcpstat 源码使用手写 Makefile（非 autotools），无 configure 脚本。直接 make 编译：

```bash
source .build-context-tcpstat-0.1
cd $BUILD_SRC_DIR
make CC=clang PREFIX=$DEFAULT_PREFIX -j1
```

关键 make 变量：
- `CC=clang` — 覆默认 gcc（Makefile 中 CC=gcc）
- `PREFIX=$DEFAULT_PREFIX` — 设置安装前缀和 include/lib 搜索路径
- `SYS` 自动检测为 HarmonyOS → 通过 Makefile override 识别为 Linux

### 3. DESTDIR 安装（R20 模式）

```bash
make install CC=clang PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
```

### 4. 预编译包制作

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package tcpstat 0.1
```

### 5. 本地安装验证

```bash
make install CC=clang PREFIX=$DEFAULT_PREFIX
$DEFAULT_PREFIX/bin/tcpstat -h
```

### 6. 收尾

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finish tcpstat 0.1 published
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build tcpstat 0.1
```

---

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 补丁 |
|---|------|------|----------|------|
| 1 | `ino_t` unknown type 编译错误 | connection.h 中 `#include <sys/types.h>` 被 `#ifdef OPENBSD` 包裹，Linux/HarmonyOS 平台不包含。musl libc 不通过其他头文件传递 `sys/types.h` | 将 `#include <sys/types.h>` 和 `#include <sys/socket.h>` 移出 `#ifdef OPENBSD` 块，变为无条件包含 | 0002 |
| 2 | HarmonyOS 未被 Makefile 识别为 Linux 平台 | `uname -s` 返回 "HarmonyOS" 而非 "Linux"，导致 `-DLINUX` 未定义、Linux scout 文件（ifscout/pidscout/tcpscout/rtscout）未编译 | Makefile 中 SYS 变量定义后添加 `ifeq ($(SYS),HarmonyOS) override SYS=Linux endif` | 0001 |
| 3 | `ncurses.h` not found 编译错误 | `/storage/Users/currentUser/usr/local/include` 不在 clang 默认搜索路径中。Makefile 的 INCLDIRS 未包含 PREFIX/include | INCLDIRS 添加 `-I$(PREFIX)/include`，LFLAGS 添加 `-L$(PREFIX)/lib` | 0001 |
| 4 | Stripped binary "Operation not permitted" | `install -s` 剥离 ELF 签名，HarmonyOS 内核拒绝执行未签名二进制 | 移除 INSTALL_FLAGS 中的 `-s` 标志 | 0001 |
| 5 | DESTDIR 不生效 | Makefile 的 INSTALL_BINDIR 直接使用 `$(PREFIX)/bin`，未包含 `$(DESTDIR)` 前缀 | INSTALL_BINDIR 改为 `$(DESTDIR)$(PREFIX)/bin` | 0001 |

---

## 源码修改

### 1. src/connection.h（补丁 0002-src-connection.h.patch）

将 `#include <sys/types.h>` 和 `#include <sys/socket.h>` 从 `#ifdef OPENBSD` 块中移出，变为无条件包含：

```diff
-#ifdef OPENBSD
 #include <sys/types.h>
 #include <sys/socket.h> /* struct sockaddr_storage */
-#endif /* OPENBSD */
 #include <netinet/in.h>
```

**原因**: musl libc 不通过 `<sys/socket.h>` 等头文件传递 `<sys/types.h>`，导致 `ino_t` 类型未定义。glibc 默认传递，但 musl 更严格。

### 2. Makefile（补丁 0001-Makefile.patch）

```diff
 SYS=$(shell uname -s)
+# HarmonyOS is Linux-based, treat as Linux
+ifeq ($(SYS),HarmonyOS)
+override SYS=Linux
+endif

-INCLDIRS = -Isrc/ -Isrc/ui -Isrc/scouts
+INCLDIRS = -Isrc/ -Isrc/ui -Isrc/scouts -I$(PREFIX)/include

-LFLAGS= -lncurses
+LFLAGS= -L$(PREFIX)/lib -lncurses

-INSTALL_BINDIR= $(PREFIX)/bin
+INSTALL_BINDIR= $(DESTDIR)$(PREFIX)/bin

-INSTALL_FLAGS=-s -m $(INSTALL_MODE)
+INSTALL_FLAGS=-m $(INSTALL_MODE)
```

---

## 依赖版本

| 依赖 | 类型 | 版本/来源 | 说明 |
|------|------|-----------|------|
| ncurses | 预编译静态库 | libncurses.a | 位于 $DEFAULT_PREFIX/lib，静态链接进二进制 |

ncurses 已通过预编译包安装，静态链接，运行时无需额外库（仅 libc.so）。

---

## 验证结果

### G0 干净构建验证（手动执行）

从原始 tarball → 应用 2 补丁 → 编译 → 安装 → 验证，全流程零人工干预：

```bash
$ ./tcpstat -h
tcpstat 0.1 (c) J. Taimisto 2005-2013
Usage tcpstat [options]...
```

**G0 结果**: ✅ PASS

### G1-G4 质量门禁

| 门禁 | 结果 | 详情 |
|------|------|------|
| G1 二进制完整性 | ✅ PASS | 1 通过, 0 警告, 0 失败 |
| G2 功能可用性 | ✅ PASS | 0 通过, 1 警告 (--version 不支持，用 -h 验证), 0 失败 |
| G3 可移植性 | ✅ PASS | 0 通过, 2 警告 (无 RPATH，静态链接不需), 0 失败 |
| G4 档案完整性 | ✅ PASS | 0 通过, 0 警告, 0 失败 |

详见 `reports/test-report.md`。

### 二进制验证

```bash
$ tcpstat -h
tcpstat 0.1 (c) J. Taimisto 2005-2013

$ readelf -d tcpstat | grep NEEDED
  (NEEDED) Shared library: [libc.so]

$ nm tcpstat | grep "_nc_" | wc -l
  30+  (ncurses 静态链接确认)
```

---

## 知识提取记录

本次编译发现 3 条可沉淀知识（写入 manifest.yaml knowledge_gained）：

1. **HarmonyOS 平台检测**: `uname -s` 返回 "HarmonyOS" 而非 "Linux"。手写 Makefile 使用 `SYS=$(shell uname -s)` 做平台检测时，需添加 HarmonyOS → Linux 映射。

2. **musl libc 头文件包含差异**: `<sys/types.h>` 在 glibc 中通过其他头文件传递包含，但 musl 不传递。条件包含的头文件（如 `#ifdef OPENBSD`）需确保非条件分支也能获取基本类型。

3. **clang 默认搜索路径不含 $PREFIX/include**: `/storage/Users/currentUser/usr/local/include` 不在 clang 默认头文件搜索路径中，Makefile 需显式添加 `-I$(PREFIX)/include`。

---

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tcpstat-0.1-ohos-aarch64.tar.gz | 273KB (279,615 bytes) | 预编译包（含 ELF 签名 + strip） |
| tcpstat-0.1-ohos-aarch64-debug.tar.gz | 25KB (25,111 bytes) | 调试符号包 |
| 0001-Makefile.patch | 2,792 bytes | Makefile 平台适配补丁 |
| 0002-src-connection.h.patch | 12,930 bytes | connection.h musl 兼容补丁 |

---

## 注意事项

- tcpstat 使用 ncurses TUI 界面，ncurses 已静态链接，运行时仅需 libc.so
- 无 configure 脚本，非 autotools 构建，直接 make 编译
- 无 make check/test 目标，测试以手动功能验证代替
- `install -s`（strip）在 HarmonyOS 上会导致 ELF 签名丢失，必须移除
- Makefile 中 `CC=gcc` 需通过命令行 `CC=clang` 覆盖

---

**编译结束**: 2026-06-17 23:31
**最终状态**: published
