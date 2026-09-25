# tpm2-tss 4.2.0 适配笔记

## 用途与在依赖链中的位置

tpm2-tss（tpm2-software/tpm2-tss）是 TPM 2.0 的通用**软件栈**，提供
`libtss2-esys`（高层 ESAPI）/ `libtss2-mu` / `libtss2-rc` / `libtss2-tctildr`
及各类 `libtss2-tcti-*` 传输层。

**本包是 gnupg 测试链的上游**，拓扑序：

```
tpm2-tss (本包)  →  swtpm (TPM 模拟器，运行时)  →  gnupg tests/tpm2dtests
```

gnupg 的 `configure` 先用 `AC_SEARCH_LIBS([Esys_Initialize], [tss2-esys])` 探测 libtss，
**只有探测到 libtss 才会执行 `AC_PATH_PROG(SWPM, swtpm)`**（configure.ac:1600-1606
把 swtpm/tpm_server 探测嵌在 `have_libtss != no` 分支内）。两者缺一，
`AM_CONDITIONAL(TEST_LIBTSS, ...)` 为假 → `tests/tpm2dtests` 不进 SUBDIRS → 4 项不执行。

装上本包后实测 gnupg configure：

```
checking for library containing Esys_Initialize... -ltss2-esys
checking for Esys_TR_GetTpmHandle in -ltss2-esys... yes
checking for swtpm... no          ← 该探测仅在 have_libtss != no 时才会出现
```

即 `have_libtss ≠ no` 已达成，gnupg 侧剩余缺口只有 swtpm。

## 方案

- 构建系统 autotools。依赖 `openssl/3.5.6`（ESYS 默认加密后端 `--with-crypto=ossl`），
  与 gnupg/2.5.22 同版本，避免同图两个 openssl。
- 关闭 fapi / policy 两层：它们需要 json-c / libcurl / uuid，而 gnupg 只用 esys+tcti。
  收窄依赖面。
- `--disable-static` 只出共享库（gnupg 以 `-ltss2-*` 动态链接消费）。

## 补丁（4 个）

| # | 目标 | 作用 |
|---|------|------|
| 0001 | `config.guess` | 加入 HarmonyOS 三元组识别（4.2.0 自带文件 `grep -c ohos` = 0） |
| 0002 | `config.sub` | ① os 识别加 ohos/linux-ohos；② **kernel-os 白名单加 `linux-ohos*`**——只改 ① 不够，否则仍报 `Kernel 'linux' not known to work with OS 'ohos'` |
| 0003 | `configure` | `umask 077` → `022`（HMDFS 上 077 使 config.status 无法创建临时目录，E114 同类） |
| 0004 | `Makefile.in` | `TESTS_CFLAGS` 加 `-U_FORTIFY_SOURCE`（见下） |

补丁 0001/0002 由仓库脚本 `scripts/patch-autotools-ohos.pl` 生成，与本仓其他
autotools 库一致。

## 测试期两个专门问题（都已修，均在 build() 内 + 0004 补丁）

### ① `_FORTIFY_SOURCE` 使 cmocka 的 `--wrap` 打桩失配

上游自带 `AX_ADD_FORTIFY_SOURCE`（`--enable-defaultflags` 默认开），其
`-D_FORTIFY_SOURCE=2` 会把 libc 调用**编译期改写**为 `__read_chk`/`__write_chk`，
而 `-Wl,--wrap=read` 只能拦普通符号 `read` → 桩函数从不被调用 →
cmocka 报 `Has remaining non-returned values: __wrap_read`。
实测命中 6 项（`io`、`tcti-{mssim,swtpm,device,pcap}`、`tctildr-getinfo`）。

秒级诊断（编译真实调用点、看符号）：

```sh
$CC -O2 -D_FORTIFY_SOURCE=2 -c src/util-io/io.c -o /tmp/p.o && nm -u /tmp/p.o | grep _chk
# → __read_chk __write_chk      （追加 -U_FORTIFY_SOURCE 后消失）
```

落点很关键：调用点在**库对象**（`src/util-io`、`src/tss2-tcti`）里，只改
`TESTS_CFLAGS` 够不到；覆盖全局 `CPPFLAGS` 又会让 `src/tss2-esys` 的 openssl 头找不到。
最终做法在配方 `_run_upstream_checks()` 内：删受影响对象（**必须连 `.a` 一起删**，
陈旧归档会带回 fortified 副本）→ 以剥掉 fortify 的 `CPPFLAGS` 重编并跑测试 →
再以原参数重建，**交付的 .so 仍保留 hardening**（实测 `libtss2-esys.so` 仍含 `__*_chk`）。

### ② 静态 cmocka 使框架自身 calloc 也被 `--wrap=calloc` 拦截

`tctildr-getinfo` 用 `-Wl,--wrap=calloc` 模拟分配失败。若 cmocka **静态**链入
（`libcmocka.a`，ohpcd 现有变体即 `shared=False`），cmocka **自身**的簿记 calloc
也会被重定向到 `__wrap_calloc` → 框架拿到"给被测代码的假指针" → **8/8 用例 rc=139**。

独立对照探针（同一测试程序，只换框架链接形态）：
静态 → 崩溃；动态 → 正常。真实用例：`tctildr-getinfo` 由 SIGSEGV 转为 **12/12 PASSED**。

修法：`default_options` 里 `cmocka/*:shared = True`。
配套两点：① 共享框架使测试二进制运行期需要 `libcmocka.so.0`，须把其 lib 目录
作为 **make 命令行变量**传入 `LD_LIBRARY_PATH`（用 `self.run(env=...)` 会被 conan
重新应用的 buildenv 覆盖，实测全部 exit 127）；② 与上一条 fortify 一并处理。

### ③ `libcrypto.pc` 的 prefix 畸形 → `openssl/bn.h' file not found`（CI #55416）

依赖本身没问题：ohpcd 的 `openssl/3.5.6` 已装、包目录里 `include/openssl/bn.h`
确实存在。问题出在 `PKG_CHECK_MODULES([CRYPTO],[libcrypto])` 递给编译器的 `-I`。

该包内的 `libcrypto.pc` 里 `prefix` 是**畸形拼接值**——包目录直接接上打包时的
构建目录、中间连分隔符都没有：

```
prefix=/storage/.../p/opens<id>/pstorage/Users/.../p/b/opens<hash>/p
```

于是 `pkg-config --cflags libcrypto` 返回一个**不存在**的 `-I`，编译
`src/tss2-esys/esys_crypto_ossl.c` 时报 `fatal error: 'openssl/bn.h' file not found`。

**configure 阶段不会报警**：`PKG_CHECK_MODULES` 只校验 `.pc` 能否解析，所以日志里
反而打印 `checking for libcrypto >= 1.1.0... yes`，把故障拖到编译期
（这种「探测说 yes、编译才炸」的形态最容易误判为依赖缺失）。

修法与 ② 同源：在 `build()` 内按依赖**真实路径**预设 `CRYPTO_CFLAGS`/`CRYPTO_LIBS`，
不依赖 `.pc`。pkg.m4 生成的探测代码在预设该变量时直接采用、跳过 pkg-config
（`if test -n "$CRYPTO_CFLAGS"; then pkg_cv_CRYPTO_CFLAGS=...`）。

实测（对**真实出错文件**预处理，工程 include 固定、只变 openssl 的 `-I` 来源）：

```sh
# 畸形 .pc 的 -I  →  src/tss2-esys/esys_crypto_ossl.c:12:10: fatal error: 'openssl/bn.h' file not found
# 预设的真实 -I    →  rc=0（全部头文件解析通过）
clang -fsyntax-only $PROJECT_INC $(pkg-config --cflags-only-I libcrypto) esys_crypto_ossl.c
clang -fsyntax-only $PROJECT_INC -I<openssl_pkg>/include          esys_crypto_ossl.c
```

> 注：CI 机器人把这次失败归类为「**网络问题**／源码下载超时」并引用了 gh-proxy URL，
> 但同一份日志里 `Sources correctly downloaded ... Uncompressing tpm2-tss-4.2.0.tar.gz`
> 明确显示源码下载、解压均成功——该判定是对日志的误读。

## 测试

`build()` 内真实执行上游 `make check`（cmocka 单元测试），以
`HMBS_UPSTREAM_TEST_RESULT` marker 输出客观计数，失败则 raise。

- **单元测试 47/47 = 100%**（`--enable-unit` 显式开启；上游默认 `no`，
  不开启时 `make check` 会以 "0 tests run" 静默通过，属假阳性）。
- 集成测试（29 项 `test/integration/*.int`）**未启用**：上游要求
  `--enable-integration`，该开关强制宿主机有 `ss`（iproute2）并连真实/模拟 TPM，
  本沙箱无 `ss`。如实申报，未计入通过率分母。
