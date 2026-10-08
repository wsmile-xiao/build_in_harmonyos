# mmlib 1.4.2 适配笔记

MindMaze 的跨平台 C 工具库（日志 / 线程 / IPC / 时间 / 文件 / 内存辅助），
上游 meson 工程（C11）。本仓首适配：官方 main 与 Conan 制品仓均无 mmlib，
版本保持 1.4.2（R37 双查不动）。

## 编译环境

- 构建系统: meson（MesonToolchain native/cross file）
- 上游版本: 1.4.2（Apache-2.0）
- 编译日期: 2026-10-03
- 编译器: clang 15.0.4（aarch64-linux-ohos，真机 /data/service/hnp/bin/clang）
- 依赖: 无第三方运行期依赖（threads/dl/rt 为系统库）；测试框架 check/0.15.2
  经 test_requires 提供（仅构建期）
- 验证: 真机 conan create 全绿（OK:4 / Fail:0，豁免后）+
  test_package 54/54；conan-verify 八门禁 Verdict PASS
  （2026-10-03T17:17:26，G0-G4 全 PASS；L2/L4/L5 无 cache 路径跳过；
  报告随档 reports/conan-verify-report.md）

## 产物

| 项 | 值 |
|---|---|
| 共享库 | `lib/libmmlib.so`（单一无版本文件，SONAME 同名）|
| 头文件 | `include/` 10 个公开头（mmargparse/mmdlfcn/mmerrno/mmlib/mmlog/mmpredefs/mmprofile/mmsysio/mmthread/mmtime）|
| pkg-config | `lib/pkgconfig/mmlib.pc` |
| DT_NEEDED | `libc.so`（仅 1 项，真机 readelf 实测；工具链默认 as-needed）|

## 关键适配决策

### 1. 单一无版本共享库（补丁 0001）

hmdfs 家目录拒绝符号链接（`ln -s` EPERM），meson 探测后打印
`Symlink creation does not work on this platform. Skipping all symlinking.`
并跳过全部 symlinking：上游 `shared_library('mmlib', version: '1.2.2')`
只安装 `libmmlib.so.1.2.2` 本体，**缺 `.so` 开发链接**——消费者
`-lmmlib` 与 CMakeDeps `find_library(mmlib)` 均不可解析。

平台规范即单一无版本文件（knowledge E330/E331；同库先例
`archives/v/vvenc/1.14.0`，OHOS 侧开 `VVENC_ENABLE_VERSIONED_SONAME=OFF`）。修复 = 去掉
`src/meson.build` 中 `shared_library` 的 `version` 参数，产出单一
`libmmlib.so`（SONAME 同名）。Linux 宿主上该参数仅影响文件名与 SONAME，
行为无差异。

### 2. shebang 脚本不可直接 execve（补丁 0002）

OHOS 内核/沙箱禁止 shebang 脚本直接执行（脚本可执行位齐全仍 EACCES，
同问题主库先例 `archives/4/4ti2/1.6.10` 的 OHOS shebang 处理）。顶层 `meson.build` 以
`run_command(find_program('read_version.py'))` 取版本号，真机 configure
阶段必然失败。修复 = 改为字面版本 `'1.4.2'`（与仓库 VERSION 文件内容
逐字节一致），消除构建期脚本执行与 python 解释器依赖。

### 3. 系统库依赖探测（无补丁）

上游 `src/meson.build` 以 `dependency('threads')` /
`find_library('dl'|'rt', required: true)`、tests 里 `find_library('m')`
取系统库。真机 clang 实测 `-ldl -lrt -lm -lpthread` 全部可链接（musl
符号并入 libc，SDK 提供兼容 stub），meson 的链接探测全部通过，无需补丁。
OHOS 工具链默认 as-needed，`libmmlib.so` 的 DT_NEEDED 不含这些 stub 库
（readelf 实测口径）。

### 4. 构建形态与注入

| # | 问题 | 处理 |
|---|------|------|
| 1 | MesonToolchain 不写 ar/ranlib；cross 侧缺 pkg-config | `_inject_meson_binaries()` 从编译器同目录推导 llvm-ar/llvm-ranlib 注入 meson ini（先例 glib/pixman）|
| 2 | 上游测试请求 `dependency('check')` | check/0.15.2 经 `test_requires` 提供（不传播消费者，先例 kea-hook gtest）；PkgConfigDeps 生成 check.pc，缺失时 `_ensure_check_pc()` 兜底 |
| 3 | check 0.15.2 通信临时文件目录（TEMP→P_tmpdir="/tmp" 只读） | `_ohos_meson_test()` 前缀 `TEMP=<TMPDIR|HOME>`；否则 check 系测试建立 fork 通信文件失败 exit 2（check_msg.c:317）|
| 4 | 重签名 | `package()` 后对 lib/**/*.so* 走 binary-sign-tool 自签（先例 glib/libwebp）|

### 5. 上游测试在 build() 内真实执行 + 平台豁免机制

native OHOS 上 `TEMP=… meson test -v --timeout-multiplier=16 --no-rebuild`
（先例 glib/pixman）；cross 跳过执行。

真机实测（2026-10-03，conan create）：5 个注册程序中 4 个全绿
（testlog / testerrno / testprofile / testinternals），testapi（420 子测试，
TAP）有 69 条失败子测试，**全部属于 29 个平台语义豁免用例**（6 类，逐条经最小探针
直连构建产物取值取证，见 `test_package/MANIFEST.yml` platform_exemptions）：

| 类别 | 用例数 | 平台根因（实测值） |
|---|---|---|
| socket | 13 | OHOS 无 IPv6 loopback：getaddrinfo(localhost) 仅 IPv4；IPv6 迭代超时（IPv4 迭代全过） |
| file | 10 | hmdfs 拒 symlink（EACCES/EPERM）与硬链接（EPERM）；权限位语义（umask=002、剥离 other 位、chmod(0) 无效）；check 中断致状态残留级联（EEXIST vs EISDIR） |
| process | 3 | aarch64 `__builtin_trap`→SIGTRAP(5) 非 SIGILL(4)；空路径 execvpe 搜索 errno EACCES(13) 非 ENOENT(2) |
| ipc | 1 | SOCK_SEQPACKET 断管写 ECONNREFUSED(111) 非 EPIPE(32) |
| thread | 1 | OHOS libc 无 robust mutex API（符号缺失）→ 退化非 robust，崩溃恢复场景永久阻塞 |
| allocation | 1 | posix_memalign(SIZE_MAX) 返回 0 且置空指针、不设 ENOMEM |

配方 `_check_ohos_test_failures()` 解析 `meson-logs/testlog.txt`：
失败集合 ⊆ 豁免名单 → 输出汇总放行；**名单外任何失败硬失败**
（TEST_QUALITY_SPEC §3.3 / ADAPTATION_GUIDE §8 机制化执行，不容忍真实回归）。

有效通过率（§3.3 公式，扣除平台豁免）：
`351 / (420 - 69) = 100%`；原始通过率 351/420 = 83.6%。

**meson 汇总 351/419 与 TAP 420 的口径说明**（评审对照要点）：meson 汇总显示
testapi `351/419 subtests passed` 并判 ERROR——419 是其行式 TAP 解析的口径
（351 ok + 68 not ok）：第 280 号失败行行首被测试子进程的无换行调试输出粘连
（testlog 原文 `837278008not ok 280 - ../tests/process-api-tests.c:process:wait_signal:
Assertion 'status & 0x00000200' failed`），meson 解析器丢弃整行。按 TAP 内容实为
**1..420 全数覆盖：420 条结果行 = 351 ok + 69 not ok**（1..420 无缺号）；配方
按子串（非行首）匹配，69 条全部识别（`_check_ohos_test_failures()` 注释即注明此
真机现象）。失败集合与豁免名单双向核对：29 个 case:subtest 恰好一一对应，
零豁免外失败（本清单 29 条 vs 实测 29 条，无遗漏无多余）。

### 6. 上游测试的两处移植性修复（补丁 0003/0004）

- 0003：`tests-child-proc` 编译 `ipc-api-tests-exported.c`（`#include
  <check.h>`）却未声明 check 依赖——check 在系统 /usr/include 时碰巧可编，
  conan 独立 prefix 下必挂（真机实测 `fatal error: 'check.h' file not
  found`；同目录 perflock/testapi/testinternals 均正确声明 libcheck）。
  补丁补上 `dependencies : [libcheck]`。
- 0004：`testlog.c` 以 `signal()+setjmp/longjmp` 捕获 abort()（SIGABRT）。
  OHOS 上普通 longjmp 跳出信号处理器后 SIGABRT 掩码不复位（POSIX：
  longjmp 不恢复信号掩码），第二次 abort 直接杀进程——testlog 先测
  mm_crash 再测 mm_check，第二个 abort 必死（真机最小复现：连捕两次
  abort，第一次成功、第二次 Signal 6 core dumped）。补丁改
  `sigsetjmp/siglongjmp/sigjmp_buf`（POSIX 正确写法）后连捕三次全过。

## test_package（消费者视角，真机 54/54 全过）

| 用例 | 结果 | 覆盖 |
|---|---|---|
| test_mmlib_api | 19/19 PASS | 链接 `mmlib::mmlib` 真实调用公开 API：mm_aligned_alloc/mm_aligned_free 对齐与读写；mm_gettime/mm_relative_sleep_ms 单调时钟；mm_thr_mutex_init/lock/trylock/unlock/deinit；mm_setenv/mm_getenv/mm_unsetenv 往返；mm_unlink + mm_get_lasterror_* 状态 |
| test_ohos_platform | 19/19 PASS | 鸿蒙特有：包内 libmmlib.so 平台 ABI 实测（ELF64/小端/ET_DYN/EM_AARCH64/PT_DYNAMIC/PT_LOAD）+ OHOS 加载器 dlopen(RTLD_NOW)/dlsym 契约符号/经 loader 调用 mm_gettime/dladdr 路径确认 |
| test_mmlib_e2e | 16/16 PASS | 消费者最小应用管线（E2E）：配置流（setenv/getenv/unsetenv 往返）；mm_ipc_connected_pair + fork 跨进程数据管线（64 项 64B 对齐载荷经库 IPC 双向收发、回传校验和逐项核对、子进程退出码 0）；mmap 共享段 + mm_thr_mutex MM_THR_PSHARED 跨进程互斥计数（父 500 + 子 500 = 1000 核对，无死锁） |

## 补丁清单

| 补丁 | 内容 |
|---|---|
| 0001 | src/meson.build 去 version 参数 → 单一无版本 libmmlib.so |
| 0002 | meson.build 版本改字面 '1.4.2'（shebang execve EACCES 规避）|
| 0003 | tests-child-proc 补 check 依赖（上游潜伏缺陷，conan 独立 prefix 下必挂）|
| 0004 | testlog.c 改 sigsetjmp/siglongjmp（OHOS abort 捕获掩码语义）|

## 复现（真机 OHOS aarch64）

```sh
# 上游测试 + 消费者测试（豁免机制内建于配方）
conan create archives/m/mmlib/1.4.2 -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64> --build=missing
# 官方八门禁
python3 scripts/ohc-run.py conan-verify mmlib 1.4.2
# Verdict PASS（2026-10-03T17:17:26；G0-G4 全 PASS，L2/L4/L5 无 cache 路径跳过）
```
