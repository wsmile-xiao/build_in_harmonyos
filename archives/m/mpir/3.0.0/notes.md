# mpir 3.0.0 适配笔记（OHOS aarch64）

适配日期：2026-09-17。执行者：macOS 协调 + 设备原生构建（HarmonyOS PC，aarch64，clang 15）。

## 1. 上游与源

- 上游：https://github.com/wbhart/mpir，tag `mpir-3.0.0`（release 附件为空，
  仅自动生成源码归档）。
- 源 URL：`https://github.com/wbhart/mpir/archive/refs/tags/mpir-3.0.0.tar.gz`
  sha256 `86a5039badc3e6738219a262873a1db5513405e15ece9527b718fcd0fac09bb2`
  （GitHub tag 归档，官方源）。
- mpir.org 官网的 tarball 链接已 302 到首页（不再托管），GitHub release 无附件，
  故选 tag 归档。tag 归档不含生成的 configure，配方在运行期判定缺失后 autoreconf 自举
  （gmp 6.3.0.1 同款模式；仓库内 199 个配方使用 autoreconf 自举且经 CI 验证）。

## 2. W0 依赖检查

- mpir/3.0.0 在 ohpcd 制品仓不存在（`conan download`/`conan install` 复探确认，
  证据 task-data/mpir-3.0.0/w0.json，version_occupancy=missing）→ 全新配方，无版本冲突。
- 无库依赖（--deps "" 显式确认）。构建期 tool_requires（均为制品仓已发布条目，
  见 §3.7）：automake/1.18、libtool/2.5.4.1；autoconf/autom4te/m4/perl 由
  设备 HNP 公共目录（/data/service/hnp/bin）提供，配方在 _bootstrap_autoreconf
  中显式钉定路径。
  - 曾考虑 tool_requires yasm/1.3.0-r4 满足 configure 的 yasm 探测，但实测制品仓
    并无该包（`conan list "yasm/*" -r=ohpcd` 0 条 + install 复探 Unable to find；
    归档 manifest 的 published 状态与远端不符）。按 R36/PF4 不引用未发布依赖，
    改以 0003 补丁将 yasm 死探测降级为软失败（见 §3.6）。

## 3. 平台适配要点（全部有实测证据）

1. **configure 自举**：autoreconf（设备 autoconf 2.73 / automake 1.18.1，均满足
   configure.ac AC_PREREQ(2.68)）。CI/构建环境 autotools 位于 profile buildenv 的
   /data/service/hnp/bin。
2. **三元组**：自带 config.guess/sub 为 GMP 包装脚本（内嵌 2015-03-08 FSF 版，
   认识 aarch64）。为避免猜错环境，与 gmp 6.3.0.1 一致显式传
   `--build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl`；
   configure.ac 的 host_cpu 分支无 aarch64 专属路径，落默认 generic C 路径
   （config.log 证实链接 mpn/generic/gmp-mparam.h）。
3. **umask 077 → 022**（HMDFS/SELinux 实撞）：autoreconf 重新生成的 configure 中
   config.status 以 `umask 077 && mktemp -d ./confXXXXXX` 建 0700 临时目录，随后
   在其中创建 subs1.awk 报 Permission denied（`config.status: error: could not
   setup config files machinery`）。自举后统一替换为 022 再 configure（gmp 6.3.0.1
   配方注释同款处理）。
4. **mpirxx.h 有符号溢出 UB（关键修复，0001 补丁）**：
   `__gmpxx_abs_ui` / `__mpz_set_si_safe` 及 plus/minus/multiplies/divides/modulus
   等运算的 si 版 eval 里 `static_cast<mpir_ui>(-l)` 与裸 `-l`，当 l =
   GMP_SI_MIN（LONG_MIN）是有符号溢出 UB。clang -O2 常量折叠出垃圾值，实测
   `LONG_MIN / mpz(2^63)` 得 0（探针：abs 期望 0x8000000000000000，实得
   0x5a0a409bc0），tests/cxx/t-ops.cc:187 断言失败。统一改为
   `- static_cast<mpir_ui>(l)`（无符号取负，模 2^64 可整除语义），移植 GMP 6
   gmpxx.h 同类修复。共 17 处 cast + 3 处三元式；补丁后 t-ops 及 cxx 套件 14/14 通过。
   此为对已安装头 mpirxx.h 的真实消费者可见修复，已纳入 test_package 回归用例。
5. **doc/info 跳过（0002 补丁）**：设备/CI 无 makeinfo，`make all` 在
   doc/mpir.info 报 Error 127。清空 doc/Makefile.am 的 `info_TEXINFOS`，
   autoreconf 后生成的 Makefile 不再依赖 texinfo。
6. **yasm 探测软化（0003 补丁）**：configure.ac 无条件要求 yasm（`which yasm`
   失败即 AC_MSG_ERROR，连 --disable-assembly 也不绕过），但 yasm 仅在 x86 族
   .asm 汇编时被调用，aarch64 generic 路径从不使用。改为找到则校验功能、
   找不到则置空继续；设备实测无 yasm 时 configure 通过，测试全绿。
7. **autotools 自举工具链（CI 实测教训，PR !10607 构建失败复盘）**：CI worker 的
   HNP 公共目录只有 autoconf.org（含 autoreconf/autoconf）与 m4，**没有
   automake（aclocal）/libtool（libtoolize）**；GitHub tag 归档无生成的
   configure，autoreconf 在 CI 报 `Can't exec "aclocal"` 而失败。设备的
   harmonybrew 恰好补齐导致 W3 全绿——典型"设备绿、CI 败"环境差异。对策：
   tool_requires 制品仓已发布的 automake/1.18 + libtool/2.5.4.1，取其
   aclocal/automake/libtoolize 脚本与数据树；conan 侧 perl/libtool 运行时
   在本平台不可用（perl/5.42.2 自带 Cwd.so 缺符号、libtoolize 内置数据目录
   为空前缀），故由配方 _bootstrap_autoreconf 组装 vendored _lt_pkgdatadir
   并显式钉定 HNP 的 perl/autoconf/autom4te/m4/autoreconf 驱动整条自举链，
   本地与 CI 同源。
8. **mp_limb_t 为 64 位**（configure 输出 "size of mp_limb_t... 8"），默认 ABI 64。

## 4. 构建与测试（R51 三步法）

- 清点：`make check` 递归 tests/ 各套件 check_PROGRAMS。st_fat/st_instrument/
  st_hamdist/st_popcount 4 个汇编对拍程序仅在同时启用 static+shared 时由
  automake 条件附加；conan 打包为 shared-only（工具链传 --disable-static），
  实际运行 **207 个测试程序**。
- 实测（W3 端到端单轮，reports/w3-local-ci.log，conan create 全程）：
  Testsuite summary 逐套件 TOTAL=PASS 且 FAIL=0——
  顶层 9 + mpn 48 + fft 20 + mpz 67 + mpq 12 + mpf 27 + misc 3 + rand 7 +
  cxx 14 = **207/207 PASS**；消费者测试 `test_mpir: all checks passed`；
  L0/L1/L4/L5 全部 pass（L2 对纯库包 skip，无 bin/）。
- 探索构建（$HOME/tmp/mpir-build-20260917，static+shared 全量）曾实测 211/211
  （含 4 个 st_* 项；t-ops 在 0001 补丁前失败，修复后通过）。
- 断言量级：tests/ 源码 ASSERT_ALWAYS 计数约 780。
- 已知探索环境差异：ssh 会话下 /data/service/hnp/bin/bash 在 HMDFS 上 getcwd
  报错导致 configure 自检失败，系统 /bin/sh 正常；conan 原生进程树内执行不受影响
  （W3 实测通过）。若 W3/CI 出现 `working directory cannot be determined`，
  优先排查 CONFIG_SHELL 指向的 bash 变体。

## 5. 消费者测试（test_package）

test.cpp 以库使用方身份调用：mpz 大数乘除回代 + 30! 数值断言 +
**mpir_si LONG_MIN 混合除法/取模回归（验证 0001 补丁）** + mpq 加法 + mpf sqrt 界。
链接 mpir::mpir（含 libmpirxx），可执行验证 L2。

## 6. 版本号

首次适配：3.0.0（上游版本，无后缀）。

## 7. 遗留与限制

- 上游 2017 年后停止维护（3.0.0 为最新发布）；如后续需要 fork 维护，按 R37 递增后缀。
- generic C 路径性能低于有汇编优化的 GMP 6（无 aarch64 asm 可用），语义一致性由
  207 项上游测试保证。
