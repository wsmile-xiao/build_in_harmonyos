# tta 2.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-10-07
- 编译器: clang / clang++
- 目标: HarmonyOS PC (aarch64)
- 状态: built

## 编译步骤

libtta 2.2 是纯 ANSI-C 的自动工具工程，产物为本机静态库 `libtta.a` 与命令行工具 `console/tta`（`SUBDIRS = . console`）。上游**没有任何自动化测试**（详见下方「上游测试」）。

1. 从 conandata.yml 的 source URL 下载 `libtta-2.2.tar.gz`（sha256 1723424d…c1435c4）并解压到源码根目录。
2. 应用补丁：
   - `0001-config-sub-aarch64.patch`：2005 版 `config.sub` 不认识 aarch64，在参数检查后加入 `aarch64-*-linux* | aarch64-*-ohos*` 分支直接原样返回，使 configure 能识别 OHOS aarch64 三元组。
   - `0002-configure-cpu-arm.patch`：把生成的 `configure` 脚本里 CPU 分支 `arm*)` 改为 `arm*|aarch64*)`，让 aarch64 归入 `CPU_ARM` 代码路径，否则 configure 会报 "CPU aarch64 is not supported"。

   > **注意**：不要改动 `configure.ac`。把它改成比 `aclocal.m4` 新会触发 automake maintainer-mode 的 `aclocal.m4` 重新生成（`make` 首条命令就是 `aclocal-1.13`），而构建环境没有 autotools，build 会失败。直接打生成的 `configure` 即可。

3. `AutotoolsToolchain` 生成 toolchain（OHOS 适配版 conan 自动给出 host/build triplet，故不在配方里手写 `--build/--host`）。
4. `autotools.configure()` → `./configure`；宿主为 aarch64 后走 `CPU_ARM` 分支。
5. `autotools.make(args=["-j1"])` → 生成 `libtta.a` 与 `console/tta`。
6. `autotools.install()` → 安装 `libtta.a` 到 lib/、`tta` 到 bin/。`libtta.h` 只是库源文件（非 `include_HEADERS`），`make install` 不装它，需在 `package()` 里 `copy` 到 include/。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 "CPU aarch64 is not supported" 并中止 | configure.ac 的 `case ${host_cpu}` 只接受 `i?86/x86_64/amd64`、`arm*`、`mipsel*`，aarch64 落入 `*)` 报错分支 | 打补丁把 `configure` 的 `arm*)` 改为 `arm*|aarch64*)`，aarch64 归入 `CPU_ARM` |
| 2 | `make` 首条命令失败：`aclocal-1.13: command not found` | 首次尝试补丁同时改了 `configure.ac`，使其比 `aclocal.m4` 新，触发 maintainer-mode 重新生成 | 撤销对 `configure.ac` 的修改，只打生成的 `configure` |
| 3 | `config.sub` 拒绝 OHOS aarch64 三元组 | 随包自带的 2005 版 `config.sub` 无 aarch64 支持 | 打补丁加入 `aarch64-*-linux* | aarch64-*-ohos*` 分支 |
| 4 | 上游仅有 `lib_LIBRARIES = libtta.a`，是纯静态库 | 无 libtool，configure 不提供 `--enable-static/--disable-shared` | 不传这些配置项；`shared` 无需处理 |
| 5b | conan create 失败：`Package type is 'library', but no 'shared' option declared` | Conan 2 中 `package_type = "library"` 必须声明 `shared` option，而 tta 是纯静态库（无 libtool，永远只产 `libtta.a`），声明一个无法兑现的 shared option 反而误导 | 改为 `package_type = "static-library"`（Conan 2 合法类型，无需 `shared` option，且不会给 configure 传任何 shared 相关 flag）；与仓库内其它纯静态 autotools 库（astronomy、adept-math）保持一致 |
| 5 | 安装后找不到头文件 | `libtta.h` 未在 `include_HEADERS` 中声明，`make install` 不安装 | `package()` 中 `copy` `libtta.h` 到 `include/` |
| 6 | 真机 `configure` 报 `shell-init: error retrieving current directory: getcwd ...` 后死于 `configure: error: working directory cannot be determined`（compile 阶段） | OHOS 工具链 profile `[buildenv]` 把 `CONFIG_SHELL` 设为 `/data/service/hnp/bin/bash`（系统 bash），autoconf 按 `$CONFIG_SHELL` 重 exec 自身；该 bash 在 HMDFS 挂载的构建目录上 `getcwd(2)` 失败（`PWD` 为空、errno Not a tty/Invalid argument/Bad address），`ac_pwd=`pwd`` 检查即死。`/bin/sh`(mksh) 同目录正常。`sh configure` 没用，因 configure 仍会被 `$CONFIG_SHELL` 劫持 | `build()` 用内联前缀 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh "<configure>" <toolchain args>` 运行 configure（内联赋值优先于 profile buildenv 导出，并会被记录进 config.status 使后续 config.status/make 也走 /bin/sh）；`make` 同加 `SHELL=/bin/sh`。`_configure_args` 保留 AutotoolsToolchain 生成的 `--prefix/--bindir/--disable-shared/--enable-static` 等全部 flag，故不改动 `generate()` |
| 7 | 修好 CONFIG_SHELL 后 configure 继续报 `config.guess: unable to guess system type` / `configure: error: cannot guess build type; you must specify one`（UNAME_SYSTEM=HarmonyOS） | OHOS 预检用 `-pr:h=ohos-aarch64 -pr:b=ohos-aarch64`（build/host 同为 OHOS aarch64），Conan 的 `AutotoolsToolchain._is_cross_building = cross_building()` 为假，因此 `_get_triplets()` 不产出 `--build/--host`；configure 未收到 `--build` 时 autoconf 调用随包 2005 版 `config.guess` 猜 build 类型，而它不认识 `HarmonyOS` | OHOS 分支在 configure 命令显式追加 `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`（与 0001 config.sub 补丁的 `aarch64-*-ohos*` 分支匹配，本机实测 config.sub 返回该三元组），autoconf 因此不再调用 config.guess |
| 8 | 真机 configure 尾声报 `./config.status[763]: can't create ./conf*/subs1.awk: Permission denied` / `config.status: error: could not setup config files machinery`（compile 阶段，HMBS 平台诊断 `[unsafe_local_mktemp]`）。日志里临时目录名 `conf38147-4383`（`conf$-$RANDOM`，**mkdir 回退已生效**）说明去掉 mktemp 分支后 **mkdir 回退仍失败** | 根因不止 mktemp：autoconf AS_TMPDIR 的 `mkdir` 回退带 `(umask 077 ...)`，HMDFS 上 setgid + 077 建出的目录对属主**不可写**，config.status 写 `subs1.awk` 时 `Permission denied`。hmbs 注入 `HMBS_AUTOCONF_MKTEMP_FALLBACK=1` 触发的 mkdir 回退同样带 077，照样失败 | 在 0003 补丁里把 mkdir 回退的 `umask 077` 改为 `umask 022`（zzuf/liblzf 同类 E011/HMDFS 先例），并让 configure 命令以 `umask 022` 前缀运行，保证 `./conf*` 临时目录可写；保留“去掉 mktemp 分支、恒走 mkdir”的决策 |
| 9 | 真机 test_package 上游回归：`bin/tta -e in.wav out.tta` 与 `bin/tta -d out.tta back.wav` **均报 `Error 255`**（encode 根因；decode 因输入 .tta 无效、roundtrip 因缺 wav 而级联失败）。consumer `test_tta` 2/2 通过（stdio 回调），但 console/tta 工具用裸 fd 就挂 | 库核心本身无恙（test.c 用 `TTA_io_callback` + `fread/fwrite/fseek` 走 stdio 概括并通过回环）。console/tta 却用裸 fd：`tta.h` 里 `tta_open_read(__name) = open(__name,O_RDONLY|O_NONBLOCK)`。在 HMFS 真机上对普通文件 `open(..., O_NONBLOCK)` 可失败（EINVAL），于是 `infile == INVALID_HANDLE_VALUE` → `tta_strerror(TTA_OPEN_ERROR)`（"can't open file"）→ `compress`/`decompress` 返回 -1 → main 返回 -1 → **退出码 255**。encode/decode 都从打开输入文件开始，故双双 255；x86_64 常规 ext4 上 O_NONBLOCK 无害，本机无法复现 | 新增 `0004-console-open-no-nonblock.patch`：把 `console/tta.h` 的 `tta_open_read` 由 `open(__name,O_RDONLY|O_NONBLOCK)` 改为 `open(__name,O_RDONLY)`。POSIX 规定 O_NONBLOCK 对普通文件读取无效果，纯去除只会更可移植，不改变正确行为（x86 本机改造后 encode/decode/roundtrip 仍全过）。**注意 `console/tta.h` 是 CRLF 行尾**，git apply 打 LF 补丁会 `patch does not apply`，故 0004 用 CRLF 上下文写成。同时 test_package 上游回归改用 `subprocess` 捕获工具真实 stdout/stderr，失败时把工具自己的报错记进日志，避免只有裸退出码 |

## 源码修改

- `patches/0001-config-sub-aarch64.patch`
- `patches/0002-configure-cpu-arm.patch`
- `conanfile.py build()`：以 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh` 内联前缀运行 configure（替代 `autotools.configure()`），make 追加 `SHELL=/bin/sh`（HMDFS 上 autoconf `$CONFIG_SHELL` 指向系统 bash 时 getcwd 失败）；OHOS 分支在 configure 命令显式追加 `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`（build/host profile 同为 OHOS aarch64 时 Conan 不自动产 triplets，需手动避免 config.guess 猜不出 HarmonyOS）。
- `patches/0003-configure-as-tmpdir-mkdir.patch`：把生成的 `configure` 里 autoconf AS_TMPDIR 的 `mktemp -d` 分支去掉，恒走 `(umask 022 && mkdir "./conf$-$RANDOM")` 路径，让 config.status 的 `ac_tmp` 指向可写目录。HMDFS `[unsafe_local_mktemp]`（mktemp 建的 `./conf*` 目录不可写且 mkdir 回退带 `umask 077` 对属主也不可写；本机 `HMBS_CAP_CHMOD=0`，无法用可执行 mktemp shim），故直接打 configure 并把 mkdir 回退的 umask 降为 022（zzuf/liblzf 同类先例）。
- `patches/0004-console-open-no-nonblock.patch`：把 `console/tta.h` 的 `tta_open_read` 由 `open(__name,O_RDONLY|O_NONBLOCK)` 改为 `open(__name,O_RDONLY)`。HMFS 上带 O_NONBLOCK 的 open 可能失败（EINVAL）→ "can't open file" → console 工具 encode/decode 均退 255。POSIX 下 O_NONBLOCK 对普通文件读取无效果，纯去除更可移植。**该文件是 CRLF 行尾**，补丁上下文用 CRLF 写、用 `git apply` 打（`patch` 工具对 CRLF 不匹配）。

## 依赖版本

无第三方编译/运行依赖。

## 上游测试

**审计与接入**：解压 `libtta-2.2.tar.gz` 后逐项检查：
- `Makefile.am` / `console/Makefile.am`：只声明 `lib_LIBRARIES` / `bin_PROGRAMS`，无 `TESTS`、`check_PROGRAMS`、`XFAIL_TESTS` 或 `check` 目标（`make check` 执行 0 用例）。
- 全树扫描：无 `tests/`、`test/`、`*_test` 源码目录，无测试框架文件，无测试脚本。
- `configure.ac`：`AC_CONFIG_FILES(Makefile console/Makefile)`，未启用任何测试框架。

因此上游**没有 formal 自动化测试**（make check 0 用例）。但发布包**自带** `console/tta`
命令行编码/解码工具（`console/Makefile.am` 的 `bin_PROGRAMS = tta`）。按仓库先例
（autotools 无 formal harness 的包，见 ccrtp/1.0.2），将对该上游自带给定工具的功能
验证提升为**上游回归套件**并在真机 test_package 中真实运行：
1. `bin/tta -e in.wav out.tta` —— 上游控制台编码器，把确定性 PCM WAV 编码成 TTA 流；
2. `bin/tta -d out.tta back.wav` —— 上游控制台解码器，解码回 WAV；
3. `cmp in.wav back.wav` —— 解码 WAV 与原 WAV 逐字节精确（roundtrip）。

MANIFEST.yml 记为 `upstream_tests_exist: true`、`upstream_test_total: 3`、
`upstream_test_count_method: python_def`（用例数由 test_package/conanfile.py 的
用例列表定义），并给出结构化 `upstream_test_audit` 与 `upstream_tests` 逐项清单。
`HMBS_UPSTREAM_TEST_RESULT` 由 test_package 每轮从真实执行的 encode/decode/roundtrip
通过数生成（缓存命中轮次同样复发）。

**test_package 消费者测试（补充覆盖，2 个用例）**：`test.c` 直接调用安装后的 `libtta.a` 公开 API：
1. `tta_binary_version()` 返回合法 `CPU_ARCH_TYPE` 枚举值（ARM 上为 `CPU_ARCH_UNDEFINED`）。
2. 完整编码→解码回环：用 stdio 背书的 `TTA_io_callback` 把一帧确定性 16-bit 单声道波形（10000 samples/8000Hz）编码成 TTA1 流，再解码回读，要求**逐字节精确**还原（含头信息字段 `nch/bps/sps/samples` 往返一致）。

`test.c` 通过自身 `tests_run/tests_failed` 计数器输出 `HMBS_TEST_PACKAGE_RESULT` 标记（discovered=passedCount=2）；为验证 harness 能真抓失败，曾故意把 `test_binary_version` 断言改成非 undefined（ARM 上必失败），确认该用例会被记为 FAIL，随后改回合法范围断言。此回环在 x86_64 本机用 gcc + `libtta.a` 实测 2/2 通过、20000/20000 字节位精确。

## 验证结果

```bash
# x86_64 本机用同一源码+补丁预验证（CPU_X86 路径，C 代码与 ARM 相同）
./configure --prefix=/usr && make -j1
# → 生成 libtta.a 与 console/tta；make check 无 TESTS，不执行
# test_package 消费者回环
gcc -I. test.c libtta.a -o test_tta && ./test_tta
# → 2/2 passed, roundtrip 20000/20000 bytes bit-exact
```

## 注意事项

- 本仓库规范按 W3 应在真机（HarmonyOS aarch64）用 conan create 执行；本机仅做逻辑/回环预验证，最终以真机预检为准。
- `tta_binary_version()` 在非 SSE 构建（含 ARM）返回 `CPU_ARCH_UNDEFINED`，属正常，测试勿断言非 undefined。
- `console/tta` 的 x86 CPUID 代码由 `CPU_X86` 宏守卫，aarch64 下不会编译，可正常构建。
