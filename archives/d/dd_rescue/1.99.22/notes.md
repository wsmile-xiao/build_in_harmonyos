# dd_rescue 1.99.22 OpenHarmony adaptation

## ⚠️ 与 GNU ddrescue 不是同一个项目

仓库内 `archives/d/ddrescue/1.30` 是 **GNU ddrescue**（gnu.org，C++，产物
`ddrescue` / `ddrescuelog`，作者 Antonio Diaz Diaz）。

本包是 **Kurt Garloff 的 dd_rescue**（带下划线，C，产物 `dd_rescue` 与
`libddr_*` 插件体系，站点 garloff.de）。两者**名近而实不同**，适配前务必按
上游 URL 区分，避免误判为重复适配（R37）。

## Source

- URL: `https://www.garloff.de/kurt/linux/ddrescue/dd_rescue-1.99.22.tar.bz2`
- 大小 215361 字节；sha256 `c15fbfce24a2bf316b5ae795d891f84e7e5ddb583ba2886a55387f40ae767041`
- 已与 fossies 记录逐字节核对一致

## Adaptation

构建系统是 **autoconf + 手写 Makefile**（不是 automake）。四个必须处理的点：

1. **无预生成 `configure`** —— 官方 tarball 只带 `configure.ac`。上游
   `autogen.sh` 做的是 `autoheader` + `autoconf`，配方在 `source()` 中做同样两件事，
   并校验 `configure` 确实生成（否则抛错，不静默继续）。

2. **`configure` 内 `umask 077` 在 HMDFS 上致命** ——
   `configure:5547/5552` 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录，
   HMDFS 上该目录权限为 `drwx--S--- (2700)`，而当前 uid（20020085）与文件
   owner（20001006）不同 → **不可写** →
   ```
   ./config.status[666]: can't create ./confOw0MTn/defines.awk: Permission denied
   config.status: error: could not setup config headers machinery
   ```
   配方把 `configure` / `config.status` 中的 `umask 077` 替换为 `umask 022`
   （实测 rc=0、`config.h` 正常生成）。

3. **`Makefile` 硬赋值 `CC = gcc`**（非 `?=`）→ 覆盖环境变量，且 OHOS 无 `gcc`。
   必须在 `make` 命令行显式传 `CC=<clang 绝对路径>`。

4. **`OS=$(shell uname)` 门控 `fstrim.o`** —— `Makefile:234-236`：
   ```make
   OS = $(shell uname)
   ifeq ($(OS), Linux)
       OBJECTS += fstrim.o
   endif
   ```
   OHOS 上 `uname` 返回 `HarmonyOS` → 条件**静默不成立** → `fstrim.o` 不入链接 →
   ```
   ld.lld: error: undefined symbol: fstrim
   >>> referenced by dd_rescue.c:1496 ... /tmp/dd_rescue-b876a8.o:(remove_and_trim)
   ```
   命令行传 `OS=Linux` 即可（实测 rc=0）。

此外：**OHOS 无 coreutils `install`**（E188），且上游 `INSTASROOT = -o root -g root`
在非 root 下必然失败 → **不调用 `make install`**，由配方按 upstream `install`
目标的布局自行落盘（`bin/` + `lib/` + `share/man/man1`）。

## Verification

- `conan create`（`ohos-aarch64` profile）：**EXIT=0**
- 门控实跑上游测试（`-o dd_rescue/*:run_upstream_tests=True`）：**EXIT=0**，
  上游 `make check` **10 个子套件全部通过、Error 数 0**
- 真实产物：`bin/dd_rescue`（252352 字节）、`lib/libddr_hash.so`、
  `lib/libddr_null.so`、`lib/libddr_crypt.so`，以及符号链接 `libddr_MD5.so`
  → `libddr_hash.so`
- `dd_rescue -V` → `dd_rescue Version 1.99.22, kurt@garloff.de, GNU GPL v2/v3`
- `test_package/run_dd_rescue_tests.sh`：**6/6 通过** —— 真实执行版本断言、
  **1MiB 数据复制 + `cmp` 逐字节比对**、插件 `dlopen` 调用，并含负向用例
  （不存在的输入必须失败）

### 上游测试的 10 个子套件（实跑清单）

| # | 子套件 | 内容 |
|---|--------|------|
| 1 | `find_nonzero tests` | `find_nonzero 2` |
| 2 | `fmt_no tests` | `fmt_no 1024200` |
| 3 | `dd_rescue tests` | `--version` + 4 组真实复制比对（`-apP` / `-b16k -B16k` / `-r` / `-x`，均接 `cmp`）|
| 4 | `dd_rescue sparse tests` | 稀疏文件处理 |
| 5 | `dd_rescue RND overwrite tests` | 随机覆盖 |
| 6 | `dd_rescue ratecontrol test` | 速率控制 |
| 7 | `dd_rescue MD5 plugin tests` | 插件 + 校验和 |
| 8 | `check_fault` | 故障注入（坏块跳过）|
| 9 | `check_crypt` | AES 全算法矩阵 + 插件链 |
| 10 | `check_sparse` | 稀疏 + 插件 |

### ⚠️ 实跑上游测试前必须修的两个**上游**问题

这两处均非本适配引入，但**不修就无法在 OHOS 上跑完**：

1. **6 个 `test_*.sh` 的 shebang 是 `#!/bin/bash`**，而 **OHOS 无 `/bin/bash`**
   → `bad interpreter: No such file or directory`（实测 `Error 126`，停在
   `check_crypt`）。配方在门控开启时改为 `#!/usr/bin/env bash`（`env` 实测可用；
   也可用 `CONFIG_SHELL` 指定绝对路径）。

2. **`test_crypt.sh:128/150` 的守卫写法有 bug**：
   ```sh
   HAVE_LZO=$(HAVE_LZO) ./test_crypt.sh      # Makefile:828 —— 传入的是字符串 "0"
   if test -n "$HAVE_LZO"; then              # "0" 非空 → test -n 为**真**
   ```
   → 即使未启用 LZO 也会进入插件链分支，去加载不存在的 `libddr_lzo.so`：
   ```
   dd_rescue: (fatal): Could not load plugin ./libddr_lzo.so
   make[1]: *** [Makefile:828: check_crypt] Error 1
   ```
   改为 `test "$HAVE_LZO" = "1"` 后通过。

> 注意区分：`test_crypt.sh:286/289` 的 `test -n "$HAVE_AESNI"` / `"$HAVE_AESARM"`
> 同理但**不能改** —— 二者来自 `grep /proc/cpuinfo`，非 Makefile 传入，
> 空值即「不适用」，`test -n` 语义正确。

> 门控 `run_upstream_tests` **默认关闭**：上游 `check` 会额外构建 6 个辅助程序
> （`find_nonzero`/`fmt_no`/`md5`/`sha256`…）并做大量磁盘 IO，不适合作为出包默认行为。
