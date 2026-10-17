# cdebconf-entropy 0.6 适配笔记

## 编译环境

- 构建系统: autotools（configure.ac + Makefile.in，tarball 内无预生成 configure）
- 上游: https://salsa.debian.org/installer-team/cdebconf-entropy（Debian Installer Team）
- 源码包: `https://deb.debian.org/debian/pool/main/c/cdebconf-entropy/cdebconf-entropy_0.60.tar.xz`（48336 字节，sha256 与 0.60 .dsc 一致：`1ebb4648…5f9b68`，已用 certutil 本地验签）
- 任务版本说明: 任务目录 `0.6` 对应上游 release `0.60`（Debian pool 从 0.28 到 0.60 无 `0.6` 发布；`0.60` 为当前稳定包，dsc Version: 0.60，源码顶层目录 `cdebconf-entropy-0.60`）
- 编译日期: 2026-09-13
- 编译器: clang/clang++
- 状态: built（待真机预检通过后由 HMBS 提交）

## 上游结构（基于 0.60 tarball 实测解包 + control 审计）

- 顶层文件：HACKING、Makefile.in、autogen.sh、configure.ac、text-plugin-entropy.c、newt-plugin-entropy.c、gtk-plugin-entropy.c、debian/
- 三个产物：cdebconf-text-entropy（文本补熵，常驻）、cdebconf-newt-entropy（newt 进度条）、cdebconf-gtk-entropy（gtk 进度条+鼠标补熵）
- 构建依赖（control）：libdebian-installer4-dev、libdebconfclient0-dev（>= 0.206）、libnewt-dev、libtextwrap-dev、libgtk2.0-dev、pkg-config
- OHOS 现状：gtk 仅有 3.24（无 gtk2）、newt/textwrap 未进仓；libdebconfclient/libdebian-installer 由 `cdebconf/0.283` 提供（requires）
- 策略：configure 自动探测——text 插件常驻构建，缺 GTK/newt 时对应插件自动跳过；不手写 stub 头，不伪造 GUI 能力

## 编译步骤

1. `get()` 解包 `cdebconf-entropy_0.60.tar.xz`
2. 不跑 autotools 自举：tarball 无预生成 configure，而真机无可用 bootstrap 链（cdebconf-terminal 0.49 在 2026-09-09 预检：`autoreconf` 缺失；conan automake/1.18 的 `aclocal` 报 `.aclocal-real: No such file or directory`；conan libtool/2.5.4 的 `libtoolize` 因缺 m4 退出）。配方因此零 `tool_requires`，用 Python 复刻 `configure.ac` 的真实逻辑——text 常驻 + `pkg-config` 探测 `libnewt` / `gtk+-x11-2.0`（回退 `gtk+-x11-3.0`）得 `FRONTENDS`，textwrap 缺席时 `TEXTWRAP_LIBS` 为空（与无该库系统上的 configure 结果一致），再把 `Makefile.in` 的 `@prefix@/@CC@/@CFLAGS@/@FRONTENDS@` 等占位符替换为真实值生成 `Makefile`（等价于 `AC_OUTPUT(Makefile)`，无 stub）
3. `make -j1`，`make install`（`prefix=<package_folder>`，产物布局与上游 `make install` 一致：`lib/cdebconf/frontend/<frontend>/plugin-entropy.so`）

## 上游测试审计（结论：无测试套件）

- 文件清单无 tests/、test/、spec/、t/ 目录
- `configure.ac`/`Makefile.in`：无 TESTS/check_PROGRAMS/check-local 目标（`make check` 为 automake 默认空目标）
- 三个 `.c` 均为插件实现（frontend/question/strutl API + `/dev/random`/mkfifo/select 逻辑），无 gtest（TEST/TEST_F）/pytest（def test_）痕迹
- 因此 `test_package/MANIFEST.yml` 声明 `upstream_tests_exist: false` 并附完整审计；test_package 的 conanfile 在真机输出 `HMBS_UPSTREAM_TEST_RESULT status:"no_tests" discovered:0 executed:0` 及原因

## test_package 设计（R34 实质验证）

- 与 cdebconf-terminal 的空安装不同：entropy 的 text 插件无 GUI 依赖，在 OHOS 上必然构建，因此测试硬要求 `text-plugin-entropy.so` 存在（非空、含 entropy 符号、真实 dlopen）；newt/gtk 则做自适应一致性验证（3 项真实断言，非硬编码、非静默跳过）：
  1. 用与 configure.ac 相同的包名（`libnewt`、`gtk+-x11-2.0`/`gtk+-x11-3.0`）在测试内重跑 pkg-config 探测并打印 rc 证据；
  2. text 插件必须存在且合法；newt/gtk 有栈则要求对应插件存在合法、无栈则要求不存在（设备将来补齐 newt/GTK 也不会静默通过）；
  3. cdebconf 硬依赖提供 libdebconfclient 与插件 API 头文件（frontend.h/question.h），且对找到的每个插件真实 dlopen。
- test_package 的 conanfile 新增 `generate()`，仅把可写 TMPDIR 注入 run 域（真机 /tmp 只读诊断的最小合规改动），不改变验证口径。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 任务版本 0.6 在 Debian pool 无对应发布 | 0.6 为 0.60 的任务侧简写（pool 只有 0.28/0.33/0.40/0.45/0.48/0.52/0.59/0.60） | 目录与 conan 版本用 0.6，源码取官方 0.60 tarball，sha256 以 0.60 .dsc 为准并在配方/manifest/notes 如实注明 |
| 2 | 本机 Windows 直连 deb.debian.org/salsa TLS 握手失败 | 出站网络限制 | 采用 .dsc 公布的 sha256（163/aliyun 双镜像一致）+ 本地 tarball 解包审计，不在配方中加非官方镜像；真机预检复验下载 |
| 3 | tarball 无 configure，真机 bootstrap 链断裂 | 同 cdebconf-terminal（真机 HMDFS 无 hardlink/chmod 能力致 conan automake 包损坏，且设备 PATH 无 m4/autoconf 套件） | 零 `tool_requires`，Python 复刻 `configure.ac`（text 常驻 + pkg-config 探测 FRONTENDS + `Makefile.in` 占位符替换），编译真实上游源码，不手写 configure |
| 4 | GTK2/VTE 0.28 与 libnewt/textwrap 在 OHOS 均无对应包 | 仓内仅 gtk3（broadway 后端，无 X11）、newt/textwrap 未进仓 | text 插件常驻构建；newt/gtk 探测自动跳过，交付上游语义下的部分安装，如实记录 |

## 验证结果

- 待 HMBS 真机预检（conan create + test_package + 上游 no_tests 证据）返回后如实回填 PR 正文通过率；本轮不猜测数字
