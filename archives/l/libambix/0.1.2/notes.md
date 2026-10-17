# libambix 0.1.2 前置适配笔记

## 边界

- 本任务只处理 `libambix/0.1.2`，落点 `archives/l/libambix/0.1.2/`。
- 未修改 `libsndfile`、`automake`、`libtool` 或任何基础设施目录。
- 认领信息：GitCode 用户名 `waylong`，队伍名称 `龙骑士`。
- issue 编号尚未在任务上下文中找到，manifest 暂记 `TBD`，拿到编号后回填。

## 版本与源码

- 上游：IEM libambix，官方地址 `https://git.iem.at/ambisonics/libambix`，
  GitHub 官方镜像 `https://github.com/iem-projects/ambix`（README 声明的镜像地址）。
- 版本 0.1.2，对应镜像 tag `v0.1.2`（2022-09-29，commit 94e2a10）。
- 源码包：`https://github.com/iem-projects/ambix/archive/refs/tags/v0.1.2.tar.gz`
- sha256：`e66994f4b776a43dba3f6719da2ba9bf9cb51c898ded4d68cb76f1b9282fe957`
 （两个官方镜像下载字节一致，同值复核通过；顶层目录 `ambix-0.1.2`）。
- 许可证：LGPL-2.1-or-later（COPYING，随包安装到 licenses）。

## W0 依赖检查

- `libsndfile/1.2.2`：仓库已有配方（`archives/l/libsndfile/1.2.2`），为上游
  `PKG_CHECK_MODULES([SNDFILE], [sndfile])` 的唯一必需依赖，已在配方
  `requirements()` 中声明。制品仓发布状态以后端 `conan download` 实测为准。
- `automake/1.18`、`libtool/2.5.4.1`：以 `tool_requires` 声明，用于 `autoreconf -fi`
  自举（与 adcli/abiword-plugin 系列配方一致的口径）。
- JACK、libsamplerate：上游可选依赖，OHOS 无已发布包，配方以
  `--without-jack --without-samplerate` 关闭其探测，不进入依赖链。
- 本机未运行 conan（按任务守则，W3 改为真机执行），以上为源码级审计结论。

## 源码与构建系统分析

- tag 包内容：`configure.ac`、`Makefile.am`、`m4/`、`libambix/`、`utils/`、
  `replacement/`、`samples/`、`doc/`；无预生成的 `configure`，必须自举。
- `configure.ac`：`AC_INIT([ambix],[0.1.2])`，libtool 库版本 `0:0:0`，
  产物 `libambix.so`；`PKG_CHECK_MODULES` 探测 sndfile/jack/samplerate；
  CoreAudio 框架检查仅在 macOS 生效；`AX_PTHREAD` 需要 pthread。
- 构建动作：直接 perl 自举（`autoreconf -fi` 在真机因 automake 垫片缺隐藏 payload 以 126 失败）→ `configure --host=aarch64-unknown-linux-ohos --without-jack --without-samplerate`（仅 --host，不传 --build，使 configure 进入交叉模式只链接不执行 conftest）→ `make -j1` → `make check -j1`。
- OHOS 适配点（均为配方层，不改上游源码）：
  - 生成的 `configure` 中 `umask 077` 替换为 `umask 022`（HMDFS 目录 setgid 约束）。
  - 构建全程固定 `-j1`（HMDFS jobserver 约束）。
  - 构建环境注入 `PWD` 与可写 `TMPDIR/TMP/TEMP`（真机构建目录 getcwd/只读 tmp 约束）。
  - OHOS 下对 `libambix/tests` 构建出的 ELF 测试程序做 `binary-sign-tool -selfSign` 自签后再执行 `make check`；`test_package` 消费者二进制同样自签（libsndfile 先例，ELF 魔数探测，不依赖 X_OK）。
  - 安装产物：`lib/libambix.so*`（或静态 `.a`）、`include/ambix/*.h`、
    `lib/pkgconfig/libambix.pc`。

## 真机失败修复（2026-09-24 预检，cannot guess build type）

- 现象：预检机 `uname -s = HarmonyOS`，automake 1.18 刚装上的
  `config.guess (2024-07-27)` 无 HarmonyOS 分支，
  `configure: error: cannot guess build type`。
- 根因：此前配方只传 `--host`、依赖 config.guess 探出 Linux 构建机；
  但预检在 HarmonyOS 本机执行，构建机本身就是 HarmonyOS，猜测必然失败。
- 修复（E007/R15，bwm-ng/0.6.3 先例）：自举后用
  `scripts/patch-autotools-ohos.pl`（内嵌 Python 兜底）给源码树下全部
  `config.guess/config.sub` 打 HarmonyOS 补丁并做 5 项校验；
  `generate()` 不再传 `--host`，剥离工具链注入的 `--build/--host`，
  以原生 `aarch64-unknown-linux-ohos` 构建（`cross_compiling=no`）。

## 上游测试盘点（口径 autotools_tests）

- 来源：`libambix/tests/Makefile.am`（v0.1.2 tag），`TESTS` 变量逐项计数，
  非 `--enable-debug` 配置（默认关闭，不计 `debug_utils`）。
- 总数 86：smoke 3（pass/skip/fail，`fail` 为 XFAIL）＋ if 变体 6
 （`fail_if1` 为 XFAIL）＋ datatest/matrix/matrices/const_matrix 4 ＋
  markers_regions 1 ＋ none_float32/none_float64 2 ＋ basic_* 4 ＋
  extended_* 8 ＋ ambix_open/close/get_sndfile/seek/seek_read/readf_int16/writef_int16 7 ＋
  basic2extended_* 51。
- 配方 `build()` 内真实执行 `make check`，从各 `test-suite.log` 的
  `# TOTAL/# PASS/# XFAIL/# SKIP/# FAIL/# XPASS/# ERROR` 汇总块聚合计数并输出
  `HMBS_UPSTREAM_TEST_RESULT` 标记（XFAIL 计入通过，XPASS/ERROR 计入失败）；
  `make check` 非零退出时仍先输出标记再抛出原错误，保证失败可审计。
- 新增测试：`test_package/test.c`，6 组有序 CHECK（order2channels、
  channels2order、is_fullset、identity 矩阵、scale 矩阵乘法、copy/create/destroy），
  输出非空且失败即非零退出；`test()` 输出 `HMBS_TEST_PACKAGE_RESULT` 标记。

## 本机轻量验证（非 conan）

- `python -m py_compile` 通过：`conanfile.py`、`test_package/conanfile.py`。
- YAML 解析通过：`conandata.yml`、`manifest.yaml`、`test_package/MANIFEST.yml`。
- C 测试源码目检：仅调用 `ambix/ambix.h` 公开 API，无空壳、无 stub。
- `conan create` 与真机 `make check` 留待 HMBS 后台预检执行，数字以真机日志为准。

## Windows 执行器说明（仅 notes 记录，不进 PR 正文）

- 本机检出上游 main 时遇到两个与本任务无关的 Windows 文件系统限制，已做本地规避，
  不影响配方内容：`archives/g/gama` 下一文件名含回车符（`core.protectNTFS=false` +
  该路径 `skip-worktree` 规避）；`archives/l/libXext` 与 `archives/l/libxext`
  仅大小写不同（4 个碰撞文件 `skip-worktree` 规避）。最终 PR 仅含
  `archives/l/libambix/0.1.2/` 新增文件。

## 真机失败修复（2026-09-24 预检，make install Error 64）

- 现象：`make check` 全绿（86 发现/81 执行/81 通过/5 跳过）后，
  `package()` 的 `make install` 倒在
  `install-nobase_includeHEADERS`：
  `runtime/.../bin/install -c -m 644 exportdefs.h ambix.h '.../p//include/ambix'`
  → `Error 64`。
- 根因：E182/E188 家族——真机 HMBS install shim（`install_shim:true`）
  只接受单文件双参形式（`[ $# -eq 2 ] || exit 64`），automake 的头文件
  批量安装规则一次传两源一目录（3 个路径参数），必挂（adms/cubelib/xeyes 先例）。
- 修复（adms 2.3.7 已过门禁同款，不碰测试）：`conanfile.py` 新增
  `_write_install_shim()`（`build_folder/_ohos_install_shim/install`，
  `os.open(0o755)` 免 chmod，`-c/-m/-d` 容错、多源逐个 `cp -f`、chmod
  `|| true`）与 `_redirect_install_to_shim()`（改写全部生成 Makefile 的
  `INSTALL/INSTALL_PROGRAM/INSTALL_SCRIPT/INSTALL_DATA` 指向 shim）；
  `build()` 在 configure 生成 Makefile 后、`make` 前接线，
  `package()` 在 `autotools.install()` 前重申（防缓存跳过 build）。
  本地 `python -m py_compile` 通过；数字以 HMBS 下一轮真机预检为准。

## 真机失败修复（2026-09-24 预检，test_package CMAKE_C_COMPILER 失效）

- 现象：上轮 install shim 修复生效（本轮 `Package built`、上游 86/81/81/0/5
  全绿），新失败在 `test_package` 的 `cmake.configure()`：
  `CMAKE_C_COMPILER: /data/service/hnp/bin/clang` 不可用，
  `Configuring incomplete`。
- 根因：profile 把 `tools.build:compiler_executables` 与
  `conan_toolchain.cmake` 烘焙为 `/data/service/hnp/bin/clang`，
  该路径在预检机上报 "inaccessible or not found"；真机实际 clang 在
  PATH（harmonybrew）。与上轮 install Error 64 不同失败域，需不同策略。
- 修复（cubelib/4.9.1 已过门禁同款，不碰测试口径）：test_package 新增
  `_resolve_compiler()`（配置路径仅文件存在时保留，否则 PATH 回退到
  clang/cc/gcc）与 `_scrub_toolchain_stale_compilers()`（ stale 路径被引用
  且本机缺失时才改写 toolchain 文件），`build()` 显式传
  `-DCMAKE_C_COMPILER/-DCMAKE_CXX_COMPILER` 双保险。

## 真机失败修复（2026-09-24 预检，rule4 passed 状态与上游结果矛盾）

- 现象：预检 evidence 门 rule4 判 incomplete：标记 status=passed 但上游 86 发现/81 执行/81 通过/0 失败/5 跳过，无 gaps 声明。
- 根因：_emit_upstream_test_result 在 failed==0 时直接发 passed，无 skipped 缺口声明；守则要求不足 100% 时 gaps 数量合计等于总数减通过数。
- 修复（不改测试口径与计数源）：聚合 test-suite.log 的 # TOTAL/# PASS/# XFAIL/# SKIP/# FAIL/# XPASS/# ERROR 保持原计数恒等式（passed+failed==executed，executed+skipped<=discovered），新增 skipped_names 逐行解析 SKIP: 条目作证据；skipped>0 且 failed==0 时附 gaps 单条目 count=skipped、category=environment，detail 说明为上游 exit 77 设计性 SKIP 自检、0 失败，evidence 列出聚合文件数与路径及 SKIP 名。本地 python -m py_compile 通过；数字以 HMBS 下一轮真机预检为准。

## 真机失败修复（2026-09-24 预检，rule4 passed 状态矛盾第 2 次修复，换策略）

- 现象：上轮补 gaps（status 仍 passed）后预检同错重现：86 发现/81 执行/81 通过/0 失败/5 跳过，rule4 仍判 passed 状态矛盾。
- 根因（与上轮不同策略）：比对仓库已放行先例 libngf/0.28（注释明示 rule4 下 passed 要求 executed==discovered）与 libm2k/0.9.0（gaps 存在即用 incomplete），确认 executed(81)!=discovered(86) 时诚实状态是 incomplete 而非 passed；上轮 passed+gaps 仍触矛盾判定。
- 修复（不改测试口径与计数源）：_emit_upstream_test_result 按 failed>0→failed、executed!=discovered→incomplete、否则 passed 三档发状态；skipped>0 时保留 gaps（count=skipped、category=environment、exit 77 设计性 SKIP 说明、聚合 test-suite.log 路径与 SKIP 名证据）并新增 reason；标记改双通道输出（output.info+print，libngf/zydis 先例）；incomplete/failed 仅告警不改构建失败语义（make check 非零仍由原 check_error 抛出）。本地 python -m py_compile 通过；数字以 HMBS 下一轮真机预检为准。
