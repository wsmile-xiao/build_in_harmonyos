# uucpsend 1.1 — 本机离线验证记录

日期：2026-10-02
主机：Windows 适配主机（无 OHOS SDK、无可用 Linux 编译环境）
范围：A 类前置适配的**本机可验证部分**。真机/shadow CI 未执行。

## 0. 本机能力边界（为什么没跑 conan create）

| 能力 | 结果 |
|---|---|
| OHOS clang 工具链 | **不可用**——`/data/service/hnp/bin/clang` 在真机上 |
| WSL Ubuntu-22.04 | **不可用**——`ext4.vhdx` 缺失，`WSL2: 找不到指定的文件 / ERROR_PATH_NOT_FOUND` |
| WSL podman-machine-default | 可启动，但 `gcc`/`cc`/`clang`/`make`/`patch` **全部缺失**，只有 python3 |
| Git for Windows | `sh.exe` 可用，但 coreutils 几乎全缺（`cat`/`mv`/`rm`/`grep`/`df`/`du` 都没有） |
| MinGW gcc 12.2.0 | 可用（`C:\mingw64\bin\gcc.exe`）——Windows 目标，无法编译 POSIX 程序 |
| GNU make 4.2.1 | 可用（`C:\mingw64\bin\mingw32-make.exe`） |
| Conan 2.29.1 | 可用，`settings.yml` 已含 `OHOS` |

因此本轮**未执行 `conan create`**（G2 闸）。已完成的是不需要 C 编译器的全部离线校验。

## 1. 源码与校验和（R39）

两个 URL 实测下载并逐字节比对：

```
https://www.infodrom.org/projects/uucpsend/download/uucpsend-1.1.tar.gz
  sha256 3447ff358e21c9927f4a35409218bf6f77c6caaceeed298bc15a8cb6dec065bc   16227 B
https://deb.debian.org/debian/pool/main/u/uucpsend/uucpsend_1.1.orig.tar.gz
  sha256 3447ff358e21c9927f4a35409218bf6f77c6caaceeed298bc15a8cb6dec065bc   16227 B
```

→ **两个 URL 完全相同**，单个 sha256 覆盖全部来源，作为等价镜像列入
`conandata.yml` 的 `sources.url` 列表。

再由 Conan 自身的下载路径复验（`conan source .`）：

```
conanfile.py (uucpsend/1.1): Sources correctly downloaded from
  https://www.infodrom.org/projects/uucpsend/download/uucpsend-1.1.tar.gz
conanfile.py (uucpsend/1.1): Uncompressing uucpsend-1.1.tar.gz to .
exit code: 0
```

解包后文件集与上游发布内容一致（11 个文件：`ChangeLog` `COPYING`
`Makefile` `log.c` `log.h` `paths.h` `readme` `uucpsend.8` `uucpsend.c`
`uucpsend.ctl` `uucpsend.ctl.5`）。

原始文件摘要（供后续比对）：

```
Makefile      f861d12522749575ae8ba4c26a29913408c2ae22067ab2c47754c3f69a537705
uucpsend.c    9b88c93dac00b9aed3c45d8710732bde9cf1e0fb27ad0f0aff1df6d1aeccac53
```

## 2. 补丁校验

### 2.1 干净套用（对 pristine 源码）

补丁生成后，对一个全新解包的 pristine 源码树先 dry-run 再实际套用，
逐 hunk 校验上下文与增删行数：

```
0001-Makefile-configurable-toolchain-and-staged-install.patch
  [ok] dry-run applied 2 hunk(s) with no context mismatch
  [ok] really applied (2 hunk(s))
0002-uucpsend.c-use-strchr-instead-of-BSD-index.patch
  [ok] dry-run applied 6 hunk(s) with no context mismatch
  [ok] really applied (6 hunk(s))
```

### 2.2 语义断言（全部通过）

Makefile：

```
[ok] SHELL pinned to /bin/sh (no bash dependency)
[ok] CC uses ?= so toolchain env wins
[ok] CFLAGS uses ?=
[ok] CPPFLAGS/LDFLAGS plumbed through
[ok] STRIP honours DEBUG
[ok] DESTDIR declared
[ok] BINDIR keeps upstream default (/usr/lib/news/bin)
[ok] CONFDIR keeps upstream default (/etc/news)
[ok] MANDIR keeps upstream default (/usr/man)
[ok] all: uucpsend target present
[ok] install depends on uucpsend
[ok] removed explicit link rule (GNU make built-in rule links it)
[ok] every install operand is $(DESTDIR)-staged
[ok] non-standard $(DEST) spelling dropped
[ok] unconditional chown-to-root removed
[ok] install -d replaced by portable mkdir -p
[ok] directories created with mkdir -p
[ok] hard-coded CC = gcc is gone
[ok] unconditional STRIP=-s is gone
```

uucpsend.c：

```
[ok] non-portable <malloc.h> removed
[ok] BSD index() call sites gone
[ok] 5 strchr() call sites
[ok] <string.h> already present for strchr()
[ok] <stdlib.h> already present for malloc()/free()
```

### 2.3 由 Conan 自己套用

```
conanfile.py (uucpsend/1.1): Apply patch (portability): Make the hand-written Makefile ...
conanfile.py (uucpsend/1.1): Apply patch (portability): Replace the BSD/legacy-POSIX index() alias ...
  patches were applied to the conan source tree: True
```

→ `apply_conandata_patches()` 在 Conan 的 source 树上真实套用成功。

## 3. Makefile 行为验证（真实 GNU make 4.2.1）

### 3.1 工具链注入方式

上游 `CC = gcc` 是 make 普通赋值，**会覆盖环境变量**。实测补丁后的 `?=` 形式：

```
=== CC set only in the ENVIRONMENT (no command-line override) ===
/env/only/clang -O3 -Wall   -c -o uucpsend.o uucpsend.c
/env/only/clang   uucpsend.o   -o uucpsend

=== CFLAGS from environment ===
/env/only/clang -O_env_flag   -c -o uucpsend.o uucpsend.c
```

→ Conan 通过 `conanbuild` 环境脚本注入的 `CC`/`CFLAGS` 真正生效（R33）。

### 3.2 默认目标与配方调用形态

```
$ make -n                      # 上游此处会报 No rule to make target 'all'
cc -O3 -Wall   -c -o uucpsend.o uucpsend.c
cc   uucpsend.o   -o uucpsend

$ make -n all CC=/data/service/hnp/bin/clang CFLAGS=-O2 -g -Wall LDFLAGS=
/data/service/hnp/bin/clang -O2 -g -Wall   -c -o uucpsend.o uucpsend.c
/data/service/hnp/bin/clang   uucpsend.o   -o uucpsend
```

### 3.3 分期安装路径（与配方 package() 的复制源一致）

```
$ make -n DESTDIR=<stage> STRIP= install
for d in <stage>/usr/lib/news/bin <stage>/etc/news <stage>/usr/man/man5 \
         <stage>/usr/man/man8; do if [ ! -d $d ]; then mkdir -p $d ; fi; done
install -m 755  uucpsend      <stage>/usr/lib/news/bin/uucpsend
install -m 644 uucpsend.ctl   <stage>/etc/news/uucpsend.ctl
install -m 644 uucpsend.8     <stage>/usr/man/man8/uucpsend.8
install -m 644 uucpsend.ctl.5 <stage>/usr/man/man5/uucpsend.ctl.5
```

默认布局与上游**逐字一致**（`/usr/lib/news/bin`、`/etc/news`、`/usr/man/man8|man5`），
只是加了 `<stage>` 前缀，且不再尝试 `chown root`。

### 3.4 DEBUG 与目录覆盖

```
$ make -n DESTDIR=<stage> DEBUG=1 install
install -m 755  uucpsend <stage>/usr/lib/news/bin/uucpsend      # -s 已消失

$ make -n DESTDIR=<stage> CONFDIR=/stage-cfg install
install -m 644 uucpsend.ctl <stage>/stage-cfg/uucpsend.ctl      # 可重定向，不写宿主机 /etc
```

## 4. test_package 期望输出核对

本机无 C 编译器，无法编译一个参考二进制，因此把 `uucpsend.c` 的
`parse_ctlfile()` / `extract_site()` / `trimm_sites()` **逐行转写**为 Python
模型，用同一批 fixture 跑出期望输出，核对断言。**这一步只用于校正 fixture
与期望值，不代替真机执行。**

转写过程中发现并修正了自己最初写错的 3 条断言：

| 原断言 | 实际行为 | 处置 |
|---|---|---|
| 无站点参数时应驱动 `/default/` | `main()` 在 `arg_sites` 为空时执行 `sites = sites->next`，**丢弃** `/default/` 头节点，实际驱动的是 `alpha` | 改为断言 `start alpha` |
| `-f extra alpha` 应同时驱动 `beta` | `trimm_sites("alpha")` 只保留 `alpha`；且上游 `parse_ctlfile` 的 else 分支用 `sites.next` 插入，`beta` 被链在 `alpha` 之前而非追加 | 改为只断言 `start alpha` |
| 日志回退断言用 `start /default/` | 同上，`/default/` 不参与本轮 | 改为 `start alpha` |

`invalid line` 诊断核对结果：

```
parse errors      : ['broken.ctl:2 invalid line.']
'invalid line'    : True
names the file    : True
has file:line=2   : True
/default/ survived: ['/default/']
```

→ 断言 2 的 `broken.ctl:2` / `invalid line` / 非中断语义均成立。

> **本机离线建模的局限（真机已证实）**：模型只覆盖了控制文件解析与站点
> 选择，**没有覆盖 `makelock()` 的失败路径**，也没有编译器可用来暴露
> `free_sites()` 的 clang 硬错误。真机首轮因此失败：一条断言写错 + 补丁
> 缺失。详见 `device-build.md`。离线建模不能替代真机，这一条已用事实证明。

## 5. 配方静态校验

```
conan graph info . -pr:h=<ohos-profile> -pr:b=<ohos-profile>
  Graph root
    conanfile.py (uucpsend/1.1): .../conanfile.py
exit 0
```

```
conan build . -pr:h=<ohos-profile> -pr:b=<ohos-profile>
  Calling generate()
  resolved toolchain: CC=/data/service/hnp/bin/clang AR=llvm-ar RANLIB=llvm-ranlib
  Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
  Calling build()
  Apply patch (portability): ...
  Apply patch (portability): ...
  RUN: make all -j1 CFLAGS=-O2 -g -Wall -fPIE -fstack-protector-strong -std=gnu89 LDFLAGS=-pie -Wl,-z,relro,-z,now
  '.' is not recognized as an internal or external command        <-- Windows cmd，非配方问题
```

配方在 Windows 上失败于最后一步是**预期行为**：Windows `cmd` 无法执行 `make`。
关键结论是 `generate()` 正确解析了工具链、`build()` 正确套用了两个补丁、
并拼出了正确的 make 命令行。真机上同一条命令会正常执行。

其他静态检查：

```
conanfile.py              -> 语法 OK，py_compile 通过
test_package/conanfile.py -> 语法 OK，py_compile 通过
test_uucpsend.sh          -> sh -n 语法 OK
conandata.yml / manifest.yaml x2 / MANIFEST.yml -> YAML OK
commands.json             -> JSON OK
全部文件                  -> LF 换行、无 BOM、无 CRLF
```

## 6. 真机验证结果（2026-10-02 已完成）

本节原为"尚未验证"清单。真机窗口已取得，结论如下（细节见 `device-build.md`）：

| 项 | 状态 | 结果 |
|---|---|---|
| `conan create`（G2 闸） | **passed** | 真机 aarch64，recipe revision `6c16e7ec…`，package id `6b129b06…` |
| `test_package`（L1） | **passed 15/15** | 首轮 14/15，失败一条是我的断言写错，已修正 |
| L4 ELF 加固 | **passed** | PIE + RELRO + NX，`NEEDED` 仅 `libc.so`，`BIND_NOW` |
| L5 产物 | **passed** | `bin/uucpsend` 在设备上实际执行成功，43456 B |
| L0/L2/L3 CI 闸门 | **pending** | 需 shadow CI 环境（W3） |
| 批处理路径端到端 | **不可达** | 需 INN spool + UUCP 传输部署 |

真机首轮失败并修复了 3 个真实缺陷（补丁缺失 `free_sites`、补丁 0001 丢
`$(OBJS)`、配方 `cwd` 指向错误目录）与 1 个平台环境问题（`make` 在
`conanbuild.sh` 被 source 后 SIGSEGV）。这些**都是本机离线阶段无法发现的**，
再次说明离线校验不能替代真机。

命令见 `next-steps.md`。
