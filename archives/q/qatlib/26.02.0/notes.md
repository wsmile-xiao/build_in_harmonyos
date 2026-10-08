# qatlib 26.02.0 适配笔记

## 编译环境
- **类型**: C + **autotools**（sdist **不含** `configure`，需 `autoreconf -fi`）
- **编译日期**: 2026-09-30
- **目标**: HarmonyOS PC（OHOS aarch64 / clang 15）
- **上游**: `intel/qatlib`（Intel QuickAssist Technology 用户态库，BSD-3-Clause）

## 本适配的具体情况
`qatlib` 是 Intel QAT **硬件**加速卡的用户态库（`libqat` + `libusdm`）。
上游只面向 x86 开发，故本适配的核心工作是**可移植性修复** + **构建系统接入**。

> ⚠️ **硬件前提**：OHOS PC 为 **aarch64**，**不存在 Intel QAT 硬件**。
> 因此本包能**正确编译、链接、并运行其内存管理 API**，但需要真实 QAT 设备的
> 功能（`icp_sal_userStart` 等）在本平台**无法验证**。这属于平台限制，已在
> `test_package/MANIFEST.yml` 与本文档如实说明，**未伪装为通过**。

## 依赖声明
上游 `configure.ac` 的 `AC_CHECK_HEADERS` / `AC_CHECK_LIB` 硬依赖：

| 依赖 | 用途 | 引用 |
|---|---|---|
| `numa.h` | NUMA 感知内存分配（`qaeMemAllocNUMA`） | `numactl/2.0.18`（**必须 shared**，见下） |
| `openssl/md5.h` | 固件校验 | `openssl/3.5.8.1` |

### ★ 关键点：numactl 必须用 **shared**
ohpcd 上的 `numactl/2.0.18` **默认 static**（`libnuma.a`）。而静态 `libnuma.a`
的符号带**版本标签**：

```
ld.lld: error: libnuma.a(libnuma.o): symbol numa_node_to_cpus@@libnuma_1.2 \
              has undefined version libnuma_1.2
```

原因：`libqat` 自身用 libtool 的 `-export-symbols-regex '^(qae)'`
（`Makefile.am:133`）生成**版本脚本**；lld 在「有版本脚本 + 引用了带版本标签的
静态符号」时会因版本节点未定义而报错。**shared `libnuma.so` 自带版本定义，可解**。

→ 配方中设 `"numactl/*:shared": True`。

> 实测对照：单独用 `-shared` 链接静态 `libnuma.a`，加不加
> `-Wl,--undefined-version` **都失败**（该 flag 在版本脚本在场时失效）；
> 只有 shared 版 numactl 才能通过。

## 4 处源码补丁（`patches/`）

| 补丁 | 文件 | 问题 | 修法 |
|---|---|---|---|
| `01-adf_platform_common-h` | `.../qat_direct/include/adf_platform_common.h` | `adf_memcpy64/128` 的 **两个分支都是 x86 SSE2 内联汇编**（`#ifdef __x86_64__` 用 `%rsi/%rdi`，`#else` 用 `%esi/%edi`）→ aarch64 无可用分支 | 把 `#else` 改为 `#elif defined(__i386__)`，并新增**非 x86 通用分支**用 `memcpy(dst, src, 64/128)`（调用方传的都是连续环形缓冲，语义等价） |
| `02-OsalServices-c` | `.../osal/src/linux/user_space/OsalServices.c` | `__GLIBC_PREREQ` 是 **glibc 专属**函数式宏，OHOS 未提供 → 编译失败 | 头部补 `#ifndef __GLIBC_PREREQ / #define __GLIBC_PREREQ(x,y) 0 / #endif` 回退，使 `#if` 退化为走 fallback 路径 |
| `03-qat_mgr-c` | `.../utilities/qat_mgr/qat_mgr.c` | `pthread_t` 在 **musl 系 C 库下是指针**，代码按整数用（`%lu` 打印、传给 `unsigned long` 形参）→ 类型错误 | 本地保存为 `unsigned long tid = (unsigned long)pthread_self()`，日志处同样显式转换 |
| `04-add-ax_pthread-m4` | `m4/ax_pthread.m4`（新增） | `configure.ac` 用 `AX_PTHREAD`，来自 **autoconf-archive**，本环境未安装 → `autoreconf` 报 `AX_PTHREAD not found` | 从仓内既有包（`babeltrace`）借用同款 `ax_pthread.m4` 加入 `m4/` |

## 构建步骤

### 1. 环境准备（本机实测要点）
```bash
export PERL5LIB=/storage/Users/currentUser/usr/local/share/automake-1.16
export PATH="/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin:$PATH"
# automake 硬编码 /usr/local/bin/autoconf（不存在）→ 用 AUTOCONF 覆盖
export AUTOCONF=/data/service/hnp/bin/autoconf
export AUTOM4TE=/data/service/hnp/bin/autom4te
export AUTOHEADER=/data/service/hnp/bin/autoheader
```
> 三处环境陷阱（逐条实测）：
> 1. `automake`/`aclocal` 找的是 `automake-1.17`，而本机只有 `1.16`
>    → `PERL5LIB` 指向 `share/automake-1.16`；
> 2. `automake` 内硬编码 `/usr/local/bin/autoconf` 且该文件不可执行
>    → 用 `AUTOCONF` 等变量覆盖为 `hnp/bin` 下的版本；
> 3. `nasm` 缺失 → 必须 `--disable-fast-crc-in-assembler`（汇编 CRC 用
>    `nasm -f elf64`，x86 专属）。

### 2. 配置
```bash
autoreconf -fi
./configure --cache-file=cross.cache \
            --disable-fast-crc-in-assembler \
            --disable-samples \
            --enable-systemd=no
```
- `--disable-samples`：示例代码含 **x86 专属 `rdtsc` 内联汇编**，必关。
- `cross.cache`：aarch64 交叉编译下 conftest 无法在构建机执行 →
  需**同时**预置 `ac_cv_prog_cc_works=yes` 与 `ac_cv_prog_cc_cross=yes`
  （只用后者不够，`AC_PROG_CC` 先查前者）。
- `--disable-fast-crc-in-assembler`：见上。

### 3. HMDFS `config.status` 陷阱（`umask 077`）
autoconf 的 `m4sh` 模板用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录
→ 权限 `0700`；而 HMDFS 上该目录属主为 `uid 20001006`（映射自 file_manager），
当前构建用户 `20020085` **无写权限** → `config.status` 写 `subs1.awk` 报
`Permission denied`。

**修法**（配方内以脚本处理）：把 `configure`（及生成的 `config.status`）中的
`umask 077` 改为 `umask 022`，并在临时目录创建块后补 `chmod 777 "$tmp"`。
同类问题仓内已有先例：`archives/a/adns/1.6.2/patches/0002-fix-config-status-hmdfs-umask.patch`。

### 4. 编译与安装
```bash
make -j4 LIBS=-lnuma
make install
```
产物：`libqat.so.4.5.0`、`libusdm.so.0.2.0` + `include/qat/*.h`（实测 rc=0）。

## ⚠️ 另外两处上游缺陷（已在本配方处理）

### ① `make install` **漏装** `qat_library_version.h`
公开头 `include/qat/icp_sal_versions.h` 以 **`#include <qat_library_version.h>`**
（**顶层**路径，非 `qat/`）引用该头，但上游 `make install` **不安装它** →
消费者一编译就 `fatal error: 'qat_library_version.h' file not found`（实测复现）。

**修法**：`package()` 中从构建树
`quickassist/lookaside/access_layer/include/qat_library_version.h`
补拷到 `include/` **顶层**。

### ② 上游无单元测试框架
`Makefile.am` 无 `TESTS` / `check_PROGRAMS` → **无 `make check` 可跑**；
唯一的示例可执行文件在 `Samples/`，但它们含 x86 `rdtsc`，且 `--disable-samples`
已将其关闭。故本包的「上游测试」实为**构建 + 安装 + 消费者编译链接实测**，
已在 marker 中如实标注 `framework: "none"`。

## 消费者测试（R34）
`test_package/test_qatlib.c`（C 程序，真实链接 `-lqat -lusdm`）：

**实测输出（全绿，rc=0）**：
```
qatlib consumer test start
OK: icp_sal_versions.h exposes ICP_API_VERSION_NUM_MAJOR
OK: cpa.h exposes CPA_API_VERSION_NUM_MAJOR == 5
OK: qaeMemAlloc(4096) returned a buffer
OK: buffer is writable
OK: qaeMemFree() cleared the pointer
OK: qaeMemAllocNUMA(4096, node=0, align=64) succeeded
OK: NUMA buffer is 64-byte aligned
OK: qatlib libqat+libusdm linked and functional
```

测试选点说明：因**无 QAT 硬件**，刻意避开需设备的接口
（`icp_sal_userStart` 等会因无设备失败），改测**能在无硬件环境真跑通且能证明
库被正确构建/链接**的部分：版本宏（头文件安装正确性）、`qaeMemAlloc/Free`
（真实分配释放）、`qaeMemAllocNUMA`（**本包 numactl 移植的关键路径**，
含 64 字节对齐断言）。空壳包无法通过。

## 注意事项
1. **numactl 必须 shared**（见上，否则 lld 报版本节点未定义）。
2. `--disable-fast-crc-in-assembler` 与 `--disable-samples` **都是必需**
   （分别对应 nasm x86 汇编与 rdtsc 示例）。
3. 本包**只有 shared**（`options.shared = [True]`）。
4. OHOS PC 无 Intel QAT 硬件 → 需设备的功能**未验证**，如实标注。
