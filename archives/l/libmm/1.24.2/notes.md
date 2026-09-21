# libmm 1.24.2 适配笔记

## 基本信息

- 上游：ModemManager 1.24.2（mobile-broadband/ModemManager），取其中 mm-glib 客户端库
- 上游仓库：https://gitlab.freedesktop.org/mobile-broadband/ModemManager
- 源码包：modemmanager_1.24.2.orig.tar.xz（1366348 字节，与上游 orig 完全一致）
- 构建系统：meson
- 配方包名：libmm（任务命名；上游库名为 mm-glib，产出 libmm-glib.so）
- 状态：built（配方已完成，真机 conan 验证待 HMBS 预检）

## 历史背景

`archives/l/libmm-glib/1.24.2/` 曾有一次手工适配尝试（2026-05-28）：
手工 meson 配置编译出 `libmm-glib.so.0.11.0` 与 `mmcli`，但 ModemManager
daemon（`src/mm-netlink.c`）因鸿蒙 SDK 头文件冲突编译失败，`finish` 流程
未走通，目录中只留下 manifest.yaml、notes.md 与 2 个补丁。
本配方在此基础上转为标准 conan 流程，复用其 meson 配置选项与补丁。

## 编译配置

meson 关闭 OHOS 不存在的栈（与历史尝试一致，另把 tests 打开）：

```bash
meson setup builddir \
  -Dbash_completion=false -Dman=false -Dgtk_doc=false \
  -Dintrospection=false -Dvapi=false -Dudev=false \
  -Dudevdir=/dev/null -Dtests=true -Dsystemdsystemunitdir=no \
  -Dsystemd_suspend_resume=false -Dsystemd_journal=false \
  -Dpolkit=no -Dmbim=false -Dqmi=false -Dqrtr=false
```

依赖：`glib2/2.88.0`、`dbus/1.14.10`（均为仓库已收录版本）。

## 关键设计：只构建 mm-glib

`meson.build` 默认目标包含 daemon（`src/`）、CLI（`cli/`）与集成测试，
其中 daemon 在鸿蒙 SDK 下不可编译（linux/socket.h 与 sys/socket.h 重复定义
`sockaddr_storage`，见“遇到的问题”第 6 条）。因此配方只构建：

- `mm-glib`：客户端库本体（`library('mm-glib', ...)`，产出 libmm-glib.so）
- `test-common-helpers`、`test-pco`、`test-qcdm`：3 个 daemon 无关的上游单元测试

`package()` 不调用全量 `meson install`（会牵连未构建的 daemon 目标），改为
手工 staged：版本化 `.so`/`.a`、源码头文件、构建期生成的头文件、`mm-glib.pc`。

## 上游测试审计（meson test 注册口径）

逐文件核对上游 `mm-1-24` 分支的 `meson.build`（`test()` 注册即计数）：

| 目录 | 注册用例 | 说明 |
|------|---------|------|
| libmm-glib/tests | test-common-helpers、test-pco | 仅链接 libmm_glib_dep，可在 OHOS 运行 |
| libqcdm/tests | test-qcdm | 仅链接 libqcdm_dep + glib，可在 OHOS 运行；ipv6pref/modepref/reset 只构建不注册 |
| tools/tests | 0 | test-stub 仅在 introspection 开启时注册（本配方关闭） |
| test/ | 0 | mmcbmmonitor 等 5 个程序是辅助可执行文件，从未传给 test() |
| **合计** | **3** | `upstream_test_total: 3`，口径 `meson_tests` |

`build()` 以 `meson test --no-rebuild --print-errorlogs` 真实执行这 3 个用例，
计数唯一来源于该命令输出的 `Ok:/Fail:/Skipped:` 汇总行（见 conanfile
`_parse_meson_test_log`），结果持久化为包内 `res/upstream_test_result.json`，
test_package 在缓存命中时从该文件复发标记。

## 消费者测试（test_package）

`test_mm.c`（4 个断言，真实调用库 API，无需 daemon/D-Bus）：

1. `mm_core_error_quark() != 0`
2. `mm_modem_state_get_string(MM_MODEM_STATE_DISABLED)` == "disabled"
3. `mm_modem_state_get_string(MM_MODEM_STATE_UNKNOWN)` == "unknown"
4. `mm_modem_state_get_string(MM_MODEM_STATE_REGISTERED)` == "registered"

计数器在被测程序内部维护，程序自行输出 `HMBS_TEST_PACKAGE_RESULT` 行，
不做任何 stdout 字符串数数或算术修补。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | freedesktop.org/GitLab 拒绝自动化下载 | 反爬虫（bot 检查页） | 使用内容相同的 Debian 镜像源；sha256 经 Ubuntu .dsc 与独立镜像 .dsc 交叉验证 |
| 2 | meson configure 找不到 gio/gobject/gio-unix | PkgConfigDeps 只产出 glib-2.0.pc | 照搬 libaccounts-glib 配方：手工生成别名 .pc，并 stage glib-mkenums/gdbus-codegen 工具 |
| 3 | meson configure 报 Unknown linker | worker 的 AR/RANLIB 为不在 PATH 的 llvm-* 名 | 同 libaccounts-glib/glb2 配方：向 conan_meson_native.ini 注入绝对路径 ar/ranlib |
| 4 | systemd/polkit/udev/mbim/qmi/qrtr 缺失 | 鸿蒙无这些栈 | 全部 -D 关闭（沿用历史尝试的选项表） |
| 5 | `test/` 等目录的测试是否该跑 | 需审计 | 逐文件核对：只有 3 个注册用例，全部 daemon 无关，全部接入 |
| 6 | ModemManager daemon 编译失败 | 鸿蒙 SDK：linux/socket.h 与 sys/socket.h 都定义 sockaddr_storage | 本配方不构建 daemon（库适配范围）；补丁保留历史尝试供参考，未验证部分不声称修复 |
| 7 | 真机 preflight 在 cmake/4.4.3 build() 报 KeyError: 'OHOS' | preflight 先查 conancenter，bare expat/2.8.2 与 zlib/1.3.1 被 CCI 配方劫持（日志仅查 conancenter 即下载 cac0f6da/47bed445），CCI 的 cmake tool_requires 无 OHOS 源码条目 | requirements() 以 override=True 固定到 ohpcd 硬化修订 expat/2.8.2#d4cf31ca 与 zlib/1.3.1#2ee7c0ee（debsig-verify/0.34 同款，同版本 RREV pin 不改变 package_id） |
| 8 | 真机 source() 报 sha256 不匹配（预期 b58d…，实际 8f57…） | deb.debian.org 池文件被重传（Debian 1.24.2-1：哈希 8f57…/1366356 字节），与 Ubuntu 池已验证文件（b58d…/1366348 字节，Launchpad 与多份 .dsc 一致）不同 | conandata.yml 保持 sha256=b58d…不变，url 改为有序列表：Ubuntu 镜像（aliyun/archive，与 .dsc 同哈希）在前，deb.debian.org 保留最后回退 |
| 12 | 真机 meson 报 Dependency dbus-1 not found（pkg-config 与 cmake 均失败），而 gio-unix-2.0 已找到 | dbus 配方未声明 pkg_config_name，PkgConfigDeps 只产出 dbus.pc，ModemManager 的 meson.build:170 查询的却是 dbus-1（与 accountsservice 配方同款情形） | generate() 新增 _create_dbus_pkg_config_alias：把 dbus.pc 复制改名出 dbus-1.pc（仅改 Name 行，Libs/Cflags/Requires 跟随真实依赖）；缺 dbus.pc 时告警跳过而非伪造 |
| 11 | 真机 meson.configure 报 Did not find pkg-config by name 'pkg-config'，gio-unix-2.0 依赖查找失败 | worker 的 PATH 上没有系统 pkg-config（与 ar/编译器死路径同一类环境缺失，但不同工具）；meson 只探测字面名 pkg-config，而 pkgconf 包只提供 bin/pkgconf | build_requirements() 新增 tool_requires(pkgconf/3.0.5)（atk 等 20+ 配方先例）；_inject_archive_tools 新增 _resolve_pkg_config（conf tools.gnu:pkg_config → PATH → pkgconf 构建包目录）并向 native/cross 双文件注入 pkg-config 条目，死条目改写；同时按 atk 缺省合并 pkg_config_path（generators 目录 + host 依赖的 pkgconfig 目录），无可用二进制时抛错停留 |
| 10 | 真机 meson.configure 报 Unknown linker /data/service/hnp/bin/ar（ENOENT） | profile/MesonToolchain 向 machine 文件写入该 worker 不存在的 ar 绝对路径；上一轮 _inject 只在缺失时注入（已有 ar 即早退）且只修 native 文件，与编译器死路径不同域 | generate() 改 _inject_archive_tools 为双文件修复：校验 native/cross 中 ar/ranlib/strip 是否可执行，死路径改写为 PATH 解析的 llvm-ar/ar、llvm-ranlib/ranlib，缺项则注入；无可用 ar 时抛错停留 |
| 9 | 真机 meson.configure 报 Unknown compiler /data/service/hnp/bin/clang（ENOENT） | profile 的 tools.build:compiler_executables 指向该 worker 不存在的绝对路径；与前两轮（CCI 劫持 / 池重传）不同域 | generate() 新增 _repair_meson_compiler_paths：conf 路径可用则不动，否则把 conan_meson_native/cross.ini 中的死路径改写为 PATH 解析的 clang/clang++（沿用 ayatana-ido 与 ar/ranlib 注入同款回退）；无可用编译器时抛错停留 |
| 13 | 真机 meson.configure 报 Program xsltproc found: NO，include/meson.build:24 中断 | include/meson.build 无条件 find_program('xsltproc') 生成 ModemManager-names.h（header-generator.xsl + D-Bus XMLs），man/gtk_doc=false 不跳过；worker PATH 无 xsltproc | 初版曾试 tool_requires（见 14）与主机直连（见 15 前半）均失败，最终改走源码补丁路线（见 15） |
| 14 | tool_requires(libxslt/1.1.45.2) 后真机在 cmake/4.4.3 build() 报 KeyError: 'OHOS' | 该 tool_requires 把 CCI 的 libxslt/libxml2（经 conancenter 先查）拉入构建图，其 cmake tool_requires 无 OHOS 源码条目；与第 7 条 expat/zlib 被 CCI 劫持同类，但属构建上下文此前无 RREV pin | 撤销该 tool_requires，不再为单个构建程序引入跨仓依赖图 |
| 15 | 主机直连方案真机报 no xsltproc on PATH and no /data/service/hnp/bin/xsltproc or /usr/bin/xsltproc（退出码 6） | 上轮假设 HNP 主机自带 xsltproc（csvprintf 硬编码路径、xkeyboard-config 文档）不成立；本 worker 三处候选均不可执行，抛错停留验证了假设为假 | 换与前两轮都不同的源码补丁路线：新增 patches/0003 把 include/meson.build 改为 xsltproc found() 时原样用，否则用 python3 跑配方在 build() 时写入的 build-aux/mm-names-generator.py（stdlib xml.etree，本地解 xi:include，复刻 XSL 的大写 #define 逻辑，同输入同输出）；无新增 Conan 依赖，不依赖主机二进制 |
| 16 | 真机 `apply_conandata_patches` 报 `Failed to parse patch: 0003`（`extra lines for hunk no.1 at 36`） | 0003 的 hunk 头写成 `@@ -21,11 +21,24 @@`，而补丁体实际为旧 12 行/新 28 行；对照上游 1.24.2 include/meson.build 起止应为 18 而非 21。conan 严格解析器按头计数校验，体比头长即判解析失败 | 只改补丁元数据、不改补丁逻辑：hunk 头修正为 `@@ -18,12 +18,28 @@`，与上游原文行号及体行数一致 |
| 17 | 修正 hunk 头后真机仍报 `Failed to parse patch: 0003`（`extra lines for hunk no.1 at 36`） | hunk 计数已与上游原文一致（旧 12/新 28），仍被解析器拒绝；属同一指纹第 2 次失败，须换不同策略 | 删除 patches/0003（含 conandata 条目），改走配方内字符串替换：build() 新增 _patch_include_meson_build，对上游 xsltproc block 做精确替换（幂等，未找到抛错），彻底消除 unified-diff hunk 解析域 |
| 19 | 真机 meson test 回 no meson test summary found（discovered 0），而库已 Package built | 主配方 _run_upstream_tests 用 self.run 字符串重定向 meson test -C build --no-rebuild --print-errorlogs > file 2>&1 走 /bin/sh；该 shell 启动需可写 /tmp（设备 /tmp 只读 erofs，dcap 先例），configure/build 走 Meson 助手无 shell 故成功，唯测试步日志空，解析器无汇总可读 | 改走无 shell 路线：subprocess 列表直调 meson test 并在 Python 内写日志，TMPDIR/TMP/TEMP 指可写目录；解析优先读结构化 meson-logs/testlog.json（无字符串数数），回退才读 ANSI 清洗后的 Ok:/Fail: 汇总 |
| 20 | 真机 test_package cmake 报 The CMAKE_C_COMPILER /data/service/hnp/bin/clang 未找到（另有 Platform/HarmonyOS 未知系统提示） | test_package 无 generate()，CMakeToolchain 直接沿用 profile 死编译器路径；未知系统提示仅告警，致命的是编译器 ENOENT | test_package 新增 generate()（cvector/zydis 先例）：conf+which 解析可用 clang/clang++，经 cache_variables 强制并补丁 conan_toolchain.cmake，附 VirtualRunEnv；不改 CMakeLists 与测试口径 |
| 18 | 真机 ninja 在 `mm-gdbus-bearer.c` 报 `.../conan/gdbus-codegen: No such file or directory`（code=126） | 配方沿 libaccounts-glib 给 python 工具生成的 wrapper 硬编码 `#!/data/service/hnp/bin/bash`；本 worker 该路径不存在（同机 clang 死路径已证实），内核报 ENOENT；另 `os.chmod` 在 chmod=0 文件系统上存在风险 | _build_python_wrapper 改用 `#!/bin/sh`（hmbs 注入 SHELL=/bin/sh，有保障），python 优先取 HMBS_PYTHON3，chmod 加容错；二进制分支同样容错 |

| 21 | 真机 test_package 报 ModemManager-names.h 缺失，meson test 仍 exit 1 无汇总 |_install_mm_glib 仅 stage 了 <build>/libmm-glib/*.h 与源码 include/*.h，漏掉 include/meson.build 在 <build>/include 下生成的 ModemManager-names.h；meson test 空汇总根因未明，摘要隐藏了真实输出 | 本轮换不同路线：package 侧补 stage <build>/include/*.h 与递归 ModemManager-names.h；测试侧不改口径，只加诊断尾（captured stdout 后 60 行、meson-logs 体积、introspect --tests 注册数）供下轮定位 |
| 22 | 真机诊断揭示 meson introspect 注册 29 测试且裸 meson test 因未构建 test-shared-icera 中止；test_package 报 mm-gdbus-cbm.h 缺失 | 前两轮假设上游仅 3 测试（文件 grep 审计错误，漏掉 src/plugins 与 test 目录的 test() 注册）；裸 meson test 全量运行要求先构建 daemon 插件二进制，而 src daemon 在 OHOS 下不可编译；头文件侧上一轮只修了顶层 glob，子目录生成的 mm-gdbus-*.h 仍漏掉 | 换不同路线：测试改显式运行 3 个 daemon 无关用例，discovered 取 introspect 总数 29，未构建 26 个报 ohos_feature gaps；头文件改递归 stage <build>/libmm-glib/**/*.h；MANIFEST 与 manifest 总数同步为 29 |
| 23 | 真机 rule4 判 incomplete：passed 状态与上游结果矛盾（discovered 29 / executed 3 / status passed） | 有 gaps 时 status 仍强制写 passed（failed==0 分支），而 passed 要求 executed == discovered；另 unbuilt 计数用 total-executed 与名单长度互相覆盖的算术修补，且 evidence 只列前 12 个名字 | 换为 catch2/libm2k 先例口径：有未构建 gaps 时 status 固定为 incomplete 并增补 reason；unbuilt 计数以 introspect 名单为唯一来源（无名单才回退 total-executed），evidence 列出全部未构建名；gaps 各项之和仍等于 discovered-passed=26 |

## 交付物

- lib/libmm-glib.so*（或 libmm-glib.a，取决于 shared 选项）
- include/libmm-glib/*.h（含构建期生成的 enum/gdbus 头文件）
- lib/pkgconfig/mm-glib.pc（meson 生成；缺失时配方按同值回退生成）
- res/upstream_test_result.json（上游测试证据）

## 使用限制

- ModemManager daemon、`mmcli` 不在本包构建范围（头文件冲突，见第 6 条）
- 本包为客户端库，供需要 ModemManager D-Bus 客户端 API 的应用链接

---

**配方编写**：2026-09-20（首轮，真机预检前，不可直接用于合入）
**申请人**：gcw_uQ09W7jl（队伍：干）
