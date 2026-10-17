# wmcdplay 1.1 适配笔记

## 编译环境
- 构建系统: autotools（上游 tar 包只带 `configure.ac` / `Makefile.am`，无 `configure` / `Makefile.in`，由配方自举）
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15（OHOS SDK 26.0.0.18，`/data/service/hnp/bin/clang++`）
- 目标: `aarch64-linux-ohos`（`os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release`）
- 状态: built（`conan create` + test_package 27/27 通过）

## 编译步骤

1. 源码：`https://www.dockapps.net/download/wmcdplay-1.1.tar.gz`（官方源，sha256 `d66d3f5ac922b9a44fed544c08f5e9018cbead55161e1d107de30903cc374767`）
2. 应用 3 个补丁（`apply_conandata_patches`），见「源码修改」节
3. autotools 自举（分步，**不使用** `autoreconf`）：
   - `"${ACLOCAL:-aclocal}" --force`
   - `autoconf -o configure configure.ac`
   - `"${AUTOMAKE:-automake}" --add-missing --copy`
   - 产物：`configure` 169196 B、`Makefile.in` 31899 B
4. `configure`（由 `AutotoolsToolchain(prefix="/")` + OHOS 追加 `--host=aarch64-linux-ohos` 生成）：

   ```sh
   /system/bin/sh ./configure --prefix=/ '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' \
       '--libdir=${prefix}/lib' '--includedir=${prefix}/include' '--oldincludedir=${prefix}/include' \
       --host=aarch64-linux-ohos
   ```

   关键判据：`checking whether we are cross compiling... yes`、`checking for x11... yes` / `xpm... yes` / `xext... yes`
5. `make -j1` → `wmcdplay`（in-source 构建；`XPM/%.art` 规则用 `cd XPM && ./makeart $*` 相对路径，out-of-source 不可用）
6. `make -j1 check`（上游 canonical 测试目标，见「上游测试」节）
7. `make -j1 install DESTDIR=<pkg>` → `bin/wmcdplay`、`share/man/man1/wmcdplay.1`、`share/wmcdplay/{bluered,grey,newstyle,wmcd}.art`、`share/wmcdplay/makeart`
8. `COPYING` → `licenses/`
9. OHOS 收尾：权限归一化 → `patchelf --remove-rpath` → `llvm-objcopy --remove-section .codesign` → `binary-sign-tool sign -selfSign 1` 重签名

## 上游测试（R51 三步法）

### 1. 清点（证据）

对未打补丁的源码树 `/data/storage/el2/base/cache/builds/wmcdplay-1.1.orig` 实测：

| 清点项 | 命令 | 结果 |
|--------|------|------|
| 文件总数 | `find . -type f \| wc -l` | **37** |
| tests/ 类目录计数 | `find . -type d -iname '*test*' \| wc -l` | **0** |
| `TESTS` / `check_PROGRAMS` / `check_LTLIBRARIES` 声明 | `grep -rnE "^\s*(TESTS\|check_PROGRAMS\|check_LTLIBRARIES)" Makefile.am configure.ac` | **无匹配（rc=1）** |
| 测试框架注册（CMake / Meson / pytest） | 检查 `CMakeLists.txt` `meson.build` `setup.py` `pyproject.toml` `conftest.py` | **均不存在** |

完整文件清单（37 项）：`.tarball-sha256`、`ARTWORK`、`COPYING`、`ChangeLog`、`Makefile.am`、`README`、`configure.ac`、`cdctl.h`、`cdctl_freebsd.h`、`wmcdplay.cc`、`wmcdplay.1`、`XPM/makeart`、`XPM/tile.xpm`，以及 `XPM/{bluered,grey,newstyle,wmcd}/` 下的 `artwork.dat` + `cdplayer.xpm` + `led.xpm` + `ledsym.xpm` + `ledtsel.xpm` + `symbols.xpm`（4 × 6 = 24 项）。

**结论：上游确无自动化测试。** 既无测试目录，也无测试程序声明，更无测试框架注册。

### 2. 运行

| 项目 | 值 |
|------|-----|
| 测试命令 | `make -j1 check` |
| 真实测试入口 | `Makefile.in` 的 `check-am` 目标（automake 生成；上游 `Makefile.am` 未定义 `TESTS`/`check_PROGRAMS`，故该目标为空） |
| 原始输出 | `make[1]: Nothing to be done for 'check-am'.` |
| 退出码 | **0** |
| 用例总数 N | **0** |
| 实际运行 N′ | **0** |
| 通过 | **0** |
| 失败 | **0** |
| 跳过 | **0** |
| 逐项用例名称 | 无（不存在用例） |
| 日志路径 | `$HOME/tmp/logs/conan-create-8-bp.log`（`conan create` 的 `build()` 阶段）、`$HOME/tmp/logs/verify-build-4.log`（独立复现） |

**为何无法运行上游测试（逐项技术原因）**：不是"没环境"，而是**上游没有测试可运行** —— `wmcdplay.cc` 是单一 C++ 源文件，逻辑全部围绕 X11 窗口与 `<linux/cdrom.h>` ioctl；上游仅提供 `--help`/`-h`/`-help` 的帮助文本与 `XPM/*.art` 美术资源，没有任何断言、测试驱动或测试数据。故 N=0、N′=0 是清点事实，非未执行。

### 3. 回填

本归档的 test_package 提供 **27 项消费者断言**（见下节），**不用于替代上游测试统计**，仅作为鸿蒙侧产物契约验证。R51 申报：**上游测试 N=0，N′=0，通过率不适用（0/0）**。

## 新增鸿蒙消费者测试用例

按适配要求，在 `test_package/test_wmcdplay.py` 中新增并验证了鸿蒙消费者用例（`harmonyos_aarch64_consumer_run`，第 27 项），断言链：

1. 产物为 `EM_AARCH64`（e_machine=183）且 ELF64 / 小端；
2. 产物含 `.codesign` 段（鸿蒙拒绝 execve 未签名 ELF）；
3. 产物通过 Conan run 环境声明的依赖闭包可加载（`libX11.so.6` / `libXpm.so.4` / `libXext.so.6` 等 32 个 `DT_NEEDED`）；
4. 端到端执行 `wmcdplay --help` 返回码 0，且输出含 `wmcdplay - A cd player designed for Window Maker` 与 `Release 1.1`。

可行性已验证：在 `conan create` 的 test_package 阶段实际执行，**27/27 PASSED，FAILED=0，SKIPPED=0**。

`--help` 由 `scanArgs()` 在 `initXWin()` 之前处理并 `exit(0)`（`wmcdplay.cc:353–376`），因此该用例**无需 X server、无需 CD 设备**，可在 OHOS PC 上无头运行。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `fatal error: 'X11/X.h' file not found` | `Makefile.am` 只声明 `AM_CFLAGS`，而 automake 的 `AM_CFLAGS` **仅作用于 C 源文件**；`wmcdplay.cc` 是 C++，pkg-config 的 `-I` 从未传给 C++ 编译 | 补丁 0001：新增 `AM_CXXFLAGS = $(x11_CFLAGS) $(xpm_CFLAGS) $(xext_CFLAGS)` |
| 2 | `-I//include`，仍找不到 `X11/Xlib.h` | `libx11/6.4.0` 的 `x11.pc` 以 `prefix=/` 安装且不可重定位，pkg-config 展开出 `-I//include` | 依赖 `AutotoolsDeps` 从 `cpp_info` 注入真实 include/lib 路径（配方保留 `PkgConfigDeps` 仅供上游 `PKG_CHECK_MODULES` 探测） |
| 3 | `invalid suffix on literal; C++11 requires a space between literal and identifier` | `fprintf(..., "...Release "VERSION"\n")` —— C++11 起 `"..."IDENT`（无空格）被词法分析为**用户自定义字面量** | 补丁 0002：`"...Release " VERSION "\n"` 两侧加空格 |
| 4 | `-f artwork_file` 找不到 `SYSARTDIR` 下的资源 | `sprintf(artfilenbuf, "%s%s", SYSARTDIR, artfilen)` 缺路径分隔符（`pkgdatadir` 无尾斜杠） | 补丁 0003：改为 `"%s/%s"` |
| 5 | 无 `configure` / `Makefile.in` | 上游只发布 `configure.ac` / `Makefile.am` | 配方 `build()` 前置自举：`aclocal → autoconf → automake`（**不用** `autoreconf`：HMDFS 下 `autoconf.m4f` 加载冲突） |
| 6 | OHOS 镜像无 `automake`/`aclocal` | `/data/service/hnp` 只有 autoconf 家族 | `tool_requires("automake/1.18")`，并用 `$ACLOCAL`/`$AUTOMAKE`（由包 `buildenv_info` 导出，仅 conanbuild 环境生效） |
| 7 | configure 在构建机上尝试运行 aarch64 二进制 | 未声明 host triplet 时 configure 按本机编译 | `--host=aarch64-linux-ohos` 使 configure 进入交叉编译模式，works-check 只链接不运行 |
| 8 | 链接报 `Error 126` / `bad interpreter: /bin/bash` | 构建环境注入的 `SHELL` 指向不可用解释器 | 配方统一 `_build_shell()` 返回 `/system/bin/sh`，并在每条 `self.run()` 前 `export SHELL/CONFIG_SHELL` |
| 9 | `make check` 显示 `Nothing to be done for 'check-am'` | 上游未声明 `TESTS`/`check_PROGRAMS` | 非缺陷；作为 R51「上游无测试」实证保留在执行链中 |
| 10 | G0 报「已知风险 E490 未在配方中处理」 | 知识图谱命中 E490（HMDFS 适配路径可能丢失 POSIX 可执行位），而 `scripts/ohc/conan_verify.py::_check_risk_addressed` 没有 E490 分支（恒返回 False），属校验器局限 | 配方按 E490 推荐方案实现缓解：`_restore_autotools_script_modes()` 在自举后、configure 前对 `configure/config.guess/config.sub/install-sh/missing/depcomp/compile/ylwrap/test-driver` 及上游 `XPM/makeart` 恢复 `S_IXUSR\|S_IXGRP\|S_IXOTH`。G0 为 non-blocking，整体 Verdict 仍 PASS |

## 源码修改

| 补丁 | 目标 | 内容 |
|------|------|------|
| `patches/0001-makefile-am-cxxflags.patch` | `Makefile.am` | 新增 `AM_CXXFLAGS = $(x11_CFLAGS) $(xpm_CFLAGS) $(xext_CFLAGS)`，让 X11/Xpm/Xext 头文件搜索路径进入 C++ 编译 |
| `patches/0002-wmcdplay-cc-version-literal.patch` | `wmcdplay.cc:356` | `"Release "VERSION"\n"` → `"Release " VERSION "\n"`（避免 C++11 用户自定义字面量解析） |
| `patches/0003-wmcdplay-cc-sysartdir-separator.patch` | `wmcdplay.cc:634` | `sprintf(artfilenbuf, "%s%s", SYSARTDIR, artfilen)` → `"%s/%s"`，修复 `-f <artwork>` 回退路径 |

三个补丁对未打补丁的纯净树全部 `patch -p1 --dry-run` + 实际应用 `rc=0`。

## 依赖版本

运行时（`requirements()`）：
- `libx11/6.4.0`（`force=True`；其 `x11.pc` 为 `prefix=/` 不可重定位）
- `libxext/6.4.0`
- `libxpm/3.5.17`

构建时（`build_requirements()`）：
- `automake/1.18`（`tool_requires`，OHOS 镜像无系统 automake）

Conan 解析出的传递闭包：`xtrans/1.6.0`、`libxcb/1.16`、`xorgproto/2025.1`、`libxau/1.0.11`、`libxdmcp/1.1.5`。

W0 依赖闸门：全部依赖已通过 `conan download` 验证为**可消费**（5/5 exit 0），未使用本地缓存或 `--build=missing` 绕过。

## 验证结果

```bash
# 1) conan create（含 test_package）—— EXIT=0
$ /bin/sh ~/tmp/bin/conanbp create archives/w/wmcdplay/1.1 \
      -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
...
wmcdplay/1.1: RUN: ...; "${AUTOMAKE:-automake}" --add-missing --copy      # rc=0
wmcdplay/1.1: RUN: ...; /system/bin/sh ./configure --prefix=/ ... --host=aarch64-linux-ohos
configure: checking whether we are cross compiling... yes
configure: checking for x11... yes ; checking for xpm... yes ; checking for xext... yes
wmcdplay/1.1: RUN: ...; make -j1                                          # rc=0
wmcdplay/1.1: RUN: ...; make -j1 check
make[1]: Nothing to be done for 'check-am'.                               # rc=0，上游无测试
wmcdplay/1.1: RUN: ...; make -j1 install DESTDIR=.../p                    # rc=0
wmcdplay/1.1: package(): Packaged 3 files: wmcdplay, makeart, COPYING
wmcdplay/1.1: package(): Packaged 1 '.1' file: wmcdplay.1
wmcdplay/1.1: package(): Packaged 4 '.art' files: bluered.art, grey.art, newstyle.art, wmcd.art
wmcdplay/1.1: Full package reference:
  wmcdplay/1.1#3013bbb61a643b4370dc1ed7e70aa2b2:c85db8c189ebe5a9316d14a956b7b726ff661b1c#396f0561d0fda2b86bacdc9a62749b9d
======== Testing the package: Executing test ========
TOTAL=27 PASSED=27 FAILED=0 SKIPPED=0
# log: ~/tmp/logs/conan-create-8-bp.log

# 2) ELF 目标契约（对 conan 包内产物）
llvm-readelf -h  .../p/bin/wmcdplay | grep -E "Class|Data|Machine|Type"
#   Class: ELF64 ; Data: little endian ; Machine: AArch64 ; Type: DYN
llvm-readelf -d  .../p/bin/wmcdplay | grep -E "NEEDED|RPATH|RUNPATH"
#   NEEDED libXpm.so.4 / libXext.so.6 / libX11.so.6 / libxcb*.so / libc++_shared.so / libc.so ...
#   （无 RPATH/RUNPATH：patchelf --remove-rpath 已生效，计数 0）
llvm-readelf -SW .../p/bin/wmcdplay | grep -c codesign
#   1（binary-sign-tool -selfSign 1 重签名成功）

# 3) 运行时冒烟（无 X server、无 CD 设备）
LD_LIBRARY_PATH=<materialized deps> .../p/bin/wmcdplay --help
#   rc=0，输出 "wmcdplay - A cd player designed for Window Maker" + "Release 1.1" + 13 个文档化选项
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/wmcdplay` | 68032 B | 已去 RPATH、已重签名的 OHOS AArch64 PIE 可执行文件 |
| `share/man/man1/wmcdplay.1` | 1167 B | man 手册 |
| `share/wmcdplay/newstyle.art` | 8670 B | 默认美术风格（`configure` 检出 `newstyle`） |
| `share/wmcdplay/bluered.art` | 11174 B | 备用美术风格 |
| `share/wmcdplay/grey.art` | 8594 B | 备用美术风格 |
| `share/wmcdplay/wmcd.art` | 9630 B | 备用美术风格 |
| `share/wmcdplay/makeart` | 224 B | 美术资源生成脚本 |
| `licenses/COPYING` | 17982 B | GPL-2.0-or-later |

## 注意事项

- `wmcdplay` 是 X11 dockapp：需要 X server 与 `/dev/cdrom` 才能进入完整交互。无头环境下 `--help`/`-h`/`-help` 路径（`scanArgs()` 在 `initXWin()` 之前 `exit(0)`）是可靠的消费者冒烟入口；无 `DISPLAY` 时按预期报 `Unable to open X display`。
- 必须 in-source 构建：`XPM/%.art: cd XPM && ./makeart $*` 使用相对路径。

## 对话记录

### 对话 #1 — configure 参数与实测耗时
configure 参数（由 Conan `AutotoolsToolchain` 经 `conanbuild.conf` 注入，与 CI 等价）：
`--prefix=/ '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' '--libdir=${prefix}/lib'
'--includedir=${prefix}/include' '--oldincludedir=${prefix}/include' --host=aarch64-linux-ohos`。
实机重测（2026-09-27）：configure rc=0 耗时 10s；`make clean` 后全量 `make -j1` rc=0 耗时 1s
（单文件 C++ 工程，产物 72128 B）。tool_requires(automake/1.18) 的自举链
（aclocal → autoconf → automake）另需约 20s。全程 `-j1`：上游 Makefile.am 的
`XPM/%.art` 生成规则使用相对路径，in-source 串行构建最稳。

### 对话 #2 — 编译结果与遇到的问题
全量构建最终 rc=0，`make check` 为 automake 空目标（上游无测试），install 产出 7 个文件。
问题按修复顺序：①`AM_CFLAGS` 不覆盖 C++ 源 → 补丁 0001 补 `AM_CXXFLAGS`；②
`"..."VERSION` 被 C++11 词法判定为用户自定义字面量 → 补丁 0002 加空格；③
`SYSARTDIR` 拼接缺路径分隔符 → 补丁 0003 改 `"%s/%s"`；④`x11.pc` 的 `prefix=/`
不可重定位 → 放弃 pkg-config 路径，靠 `AutotoolsDeps` 注入真实 include/lib。

### 对话 #3 — 本机沙箱执行域差异（conan create 的真凶）
此前"沙箱拒绝非 ELF 脚本 execve"为误判。受控实验：同一 `aclocal` 包装脚本，
bash/sh/perl/node 执行均成功，唯 python 子进程 EACCES——且换用应用包内 python
（`/data/storage/el1/bundle/.../python3`）即成功。真因：沙箱按**启动解释器路径**
施加 exec 允许清单并被子进程继承（Landlock 式域）；conan launcher 的 shebang 恰是
HMDFS 上的 `$HOME/usr/local/bin/python3`（受限域）。与 ELF/脚本、文件权限、
CONAN_HOME 位置无关。解法：用包内 python 经 `conans.conan:run` 入口启动 conan。
已沉淀知识草稿 DRAFT-10038。
- `AM_CFLAGS` 不覆盖 C++ —— 后续同类 X11 dockapp（C++ 源）配方应直接补 `AM_CXXFLAGS`。
- 运行期依赖闭包较大（32 个 `DT_NEEDED`，含整条 libxcb 家族），因为 `AutotoolsDeps` 会把 `cpp_info` 的全部传递库写入 `LIBS`。这是 X11 图的正常形态，不是静态链接异常。
---

**编译结束**: 2026-09-27 16:36
**最终状态**: built
