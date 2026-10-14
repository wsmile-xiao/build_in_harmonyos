# 适配笔记 — multimail 0.52（MultiMail 离线邮件包阅读器）

## 上游信息

- **软件**：multimail（MultiMail Offline Reader）
- **版本**：0.52（上游 tag `0.52`，2019-04-01 release）
- **上游仓库**：https://github.com/wmcbrine/MultiMail
- **主页**：http://wmcbrine.com/mmail/
- **许可证**：GPL-3.0-or-later（COPYING.md：GPLv3 or later；bluewave.h 另有 Hatchew/Cutting Edge 结构使用许可）
- **构建系统**：纯 GNU Makefile（无 configure / CMake / meson）
- **语言**：C++（mmail/ 约 20 个 .cc + interfac/ 约 15 个 .cc）
- **源码包**：https://github.com/wmcbrine/MultiMail/archive/refs/tags/0.52.tar.gz
- **sha256**：3bfbf5d410dfff8bc33dfba98a7ba382d3168b8f0d79c2cbcbe6e53be9bba24c（2026-10-14 实拉 GitHub 归档计算，221566 字节）

## 上游测试审计（2026-10-14，实拉归档逐文件验证）

- 归档共 70 个文件：顶层 Makefile/Makefile.bcc/Makefile.vc/Makefile.wcc、config.h、depend、mm.1、mmail/、interfac/、colors/；**无 tests/、test/、t/、spec/ 目录，无任何 `*test*`/`*check*` 文件**。
- 顶层 Makefile 仅 `all/clean/dep/install` 目标，**无 check/test 目标**（`make check` 无规则可执行）。
- 无 configure/CMakeLists.txt/meson.build；无 enable_testing/add_test；无 gtest/ctest/pytest 注册。
- 结论：`upstream_tests_exist: false`，`upstream_test_total: 0`（口径 `autotools_tests`，make 系构建、无测试注册），`build()` 不集成 make check，证据由 test_package 阶段 `no_tests` 标记给出（对齐 bwm/0.6.3、cvechecker/4 范例）。

## OHOS 适配决策

1. **DEBUG=Y**：OPTS=`-g -Wall -pedantic`，且跳过 `POST = strip mm` 后处理（真机 strip 不可依赖）。
2. **CURS_DIR/LIBS 覆盖**：上游默认 `CURS_DIR=.`、`LIBS=-lcurses`；配方在 make 命令行覆盖为 `CURS_DIR=<ncurses-6.6>/include`、`LIBS="-L<ncurses-6.6>/lib -lncursesw"`（ncurses/6.6 为宽字符静态库，提供顶层 `include/curses.h`，与源码 `#include <curses.h>` 对接；utalk/1.0.2 同款依赖，已合入主干）。
3. **不用上游 `make install`**：其 `install -c -s` 依赖 strip，且 `ln $(HELPDIR)/mm.1 $(HELPDIR)/mmail.1` 硬链接在 HMDFS 不可靠；`package()` 改为手动拷贝 `bin/mm` 与 `share/man/man1/mm.1`（bwm/0.6.3 手动装箱先例）。
4. **CXX 解析（R33）**：`tools.build:compiler_executables:cpp` 存在即用，否则按 `clang++ → c++ → g++` 查 PATH 与真机 SDK 目录；纯 isfile 探测，不做 X_OK 探测（R49）。
5. **SHELL/TMPDIR 加固（bwm/0.6.3 先例）**：仓库 profile  pin 的 HNP bash 在部分 HMBS 宿主不可用，`generate()` 存 `multimail_hmos_fix` 构建域脚本（SHELL=/bin/sh + 可写 TMPDIR），`build()` 另做内联 export 兜底；只读 `/tmp` 永不回退。
6. **无补丁**：首轮未改上游源码；若真机出现 curses/系统头差异再按 `refresh-patch --auto` 补 patch（默认禁平台宏，R8/PF5）。

## test_package 设计（6 项，全部真实执行）

- `mm` 是纯交互 curses 程序（无 `--help`/`--version`：任何 argv 均被当作邮件包路径并进入 UI），因此不用“跑 UI 看输出”模式，6 项如下：
  1. `bin/mm` 存在且非空；
  2. `readelf -h` 校验 ELF 类型 EXEC/DYN；
  3. `strings` 非空且含 `MultiMail`（非空输出守卫：防“空文件比空文件却报通过”类假阳性）；
  4. `strings` 含包格式标记（QWK/SOUP/Blue Wave/OMEN，源码 qwk.cc/soup.cc/bw.cc/omen.cc 实有字符串）；
  5. `mm.1` 存在、非空且含 `MultiMail`；
  6. 无头执行负向对照：`stdin=/dev/null、TERM=dumb` 下后台运行 + shell 内建 watchdog（不依赖外部 `timeout`），curses 无 TTY 必快速非零退出；hang（watchdog 击杀，rc=124）或 rc=0 均判失败，并记录 rc 与输出头 300 字节为证据。
- 证伪说明：若将 `mm` 换成 `exit 1` 空桩，测试 2（非 ELF）、3/4（无字符串）直接失败——harness 可抓失败，非 exit-0-alone。
- 标记：`test_multimail.sh` 末尾按计数器打印 `HMBS_TEST_PACKAGE_RESULT`（discovered=6 真实计数）与 `HMBS_UPSTREAM_TEST_RESULT`（no_tests）；`test_package/conanfile.py` 在 `self.run` 成功后复述两标记（cache-hit 回放，bwm/0.6.3 先例）。

## 依赖发布检查（W0）

- 唯一 Conan 依赖 `ncurses/6.6`：仓内 `archives/n/ncurses/6.6/` 已存在且已合入主干（utalk/1.0.2 用同款依赖合入，PR #13941，ohpcd 制品仓已发布）；选 6.6 而非 6.5 的原因见下「真机失败根因与修复」。

## 本地验证记录

| 检查项 | 结果 |
|--------|------|
| 上游归档下载 + sha256 | 通过（2026-10-14，见上） |
| 配方静态自检（python 语法） | 待本机执行后记录 |
| 真机 conan create + rule4 门禁 | 待 HMBS 后台预检（本轮不 commit/push） |

## 真机失败根因与修复（2026-10-14 预检 compile 失败）

- **现象**：预检 `conan create` 在编译阶段失败，尾部日志为 `ninja/1.13.2` 的 `cmake.configure()` 报错（`System is unknown to cmake … Platform/HarmonyOS` + `CMAKE_CXX_COMPILER: /data/service/hnp/bin/clang++ …`），而非 multimail 自身 Makefile 报错；前序日志显示 `ncurses/6.5: Main binary package missing` 后开始构建 ninja。
- **根因**：multimail 原依赖 `ncurses/6.5`；conancenter 同时托管 `ncurses/6.5`（仅 6.3/6.4/6.5，无 6.6），且其配方 `build_requirements()` 无条件 `tool_requires("pkgconf/2.0.3")`（除非 profile 预置 `tools.gnu:pkg_config`），而 pkgconf→meson→ninja 链条中的 ninja（CMake 构建）在当前真机 cmake 下无法配置 HarmonyOS 平台（与本包无关的工具链问题）。预检同时启用 `conancenter` + `ohpcd` 双 remote（CI 侧会禁用 conancenter），当 ohpcd 的 6.5 二进制缺失需从源码构建时，存在解析到 conancenter 配方的可能，一并拖入该工具链。
- **修复**：依赖改为 `ncurses/6.6`。conancenter 无 6.6（已核对上游 conandata 仅 6.3/6.4/6.5），只能解析到 ohpcd 的 OHOS 适配配方；该配方为纯 Autotools、零 `tool_requires`（已逐行确认无 `tool_requires`/`build_requirements`），从源码构建也不需要 pkgconf/ninja；且 utalk/1.0.2 已用同款依赖合入主干，端到端可行。multimail 仅用基础 curses 头与 `-lncursesw`，6.5→6.6 为兼容小版本 bump，构建与测试接入不变。
- **待下轮预检验证**：`conan create` 不再构建 ninja/pkgconf/meson，直接使用 ohpcd ncurses/6.6。

## 待真机确认的风险

- `libncursesw` 静态链接 `mm` 是否一次通过（符号：chtype/mousemask/panel 未用，仅基础 curses）。
- `mm.1`  troff 在 `copy` 后路径 `share/man/man1/mm.1` 是否符合 CI 对 application 包的装箱期望。
- 无头对照实测 rc（预期 curses 报 `Error opening terminal` 类非零退出；若真机有可分配 TTY 导致 rc=0，需按实测证据改判）。
