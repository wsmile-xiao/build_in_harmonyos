# rarian 0.8.6 适配笔记

## 编译环境

- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-24
- 编译器: clang/clang++
- 状态: built（待 HMBS 真机预检回填实测数字）

## 上游信息

- 主页: https://rarian.freedesktop.org/
- 仓库: https://gitlab.freedesktop.org/rarian/rarian
- 版本: 0.8.6（相对 0.8.5 将 TinyXML 升级到 TinyXML2）
- 源码: https://gitlab.freedesktop.org/rarian/rarian/-/releases/0.8.6/downloads/assets/rarian-0.8.6.tar.bz2
- sha256: 9d4f7873009d2e31b8b1ec762606b12bee5526e1fe75de48e9495382bfef2bea（实测下载 376011 字节）
- 许可证: LGPL-2.1-only（库）/ GPL-2.0（工具脚本，见 COPYING/COPYING.UTILS）
- 说明: Freedesktop 文档元数据访问库，Scrollkeeper 替代品；C 库 + C++ OMF 读取器 + scrollkeeper 兼容脚本/工具。

## 编译步骤

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

关键 configure 参数（见 conanfile.py generate）：

- `--disable-skdb-update`：安装时不执行 rarian-sk-update，避免污染宿主数据库，保持 Conan 打包无副作用
- `--disable-dependency-tracking`：OHOS 常规加速
- `--with-check`：强制启用 libcheck 测试；缺 check 时直接失败，不静默跳过
- `--localstatedir=${prefix}/var`
- 静态默认：`--enable-static --disable-shared`

构建流程：`configure` → `make -j1` → `make -j1 check`（上游测试）→ `make install -j1`。

## 上游测试盘点（申报口径）

- 位置: `tests/`（`tests/Makefile.am` 定义 `TESTS = check_rarian`）
- 入口: `tests/check-main.c` 注册 8 个 suite（utils/reg-utils/list-utils/man/language/info/ht-utils/main）
- 总数: **29** 个 libcheck `START_TEST` 用例：
  - check-rarian-language.c 2、check-rarian-ht-utils.c 2、check-rarian-info.c 3、
    check-rarian-utils.c 10、check-rarian-reg-utils.c 2、check-rarian-main.c 4、
    check-rarian-list-utils.c 2、check-rarian-man.c 4
- 统计方法: `grep -c START_TEST tests/check-*.c` 按文件累加（详见 test_package/MANIFEST.yml `upstream_test_count_method: autotools_tests`）
- 执行: `make -j1 check` 编译并运行 `tests/check_rarian`；用例级计数唯一来源是
  `tests/check_rarian.log` 中的 libcheck 汇总行 `Checks: N, Failures: F, Errors: E`
 （不用 test-suite.log 的程序级 TOTAL/PASS/FAIL，不数字符串、不做减法修补）。
- 真机实测数字待 HMBS 预检回填；本轮不猜测通过率。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Windows 检出上游 main 失败 `invalid path ... gama ... patch??` | 上游文件名尾带 `\r\r`，Windows Win32 禁止控制字符 | 本机 `git config core.protectNTFS false` 后检出成功；属本机特例，不进配方 |
| 2 | Windows 大小写不敏感导致 `archives/l/libXext` 与 `archives/l/libxext` 冲突，`git status` 恒脏 | 上游同时存在仅大小写不同的两目录 | 本机 sparse-checkout 排除大写 `archives/l/libXext/` 后状态干净；Linux 真机/CI 不受影响，不进配方 |
| 3 | 安装钩子可能执行数据库更新 | 上游 `ENABLE_SKDB_UPDATE=1` 时 `install-exec-hook` 调用 `rarian-sk-update` | 配方固定 `--disable-skdb-update` |
| 4 | configure 内 `umask 077` 在 HMDFS 下不可写 | 同 detox/chmlib 类问题 | 复用已有能力：`build()` 内将 `umask 077` 改 `umask 022` |
| 5 | 真机预检 `tinyxml2/11.0.0` 源码构建失败（`cmake.configure()`，`CMAKE_C/CXX_COMPILER` 校验不过） | `requires tinyxml2/11.0.0` 在预检远端顺序下命中 conancenter 配方（`CMakeToolchain` + `cmake.configure()`，与本仓 `self.run cmake + ohos.toolchain` 的已适配配方签名不符），其 Linux 向构建在 OHOS 下配置失败；ohpcd 无本次请求配置的可兼容二进制 | 去掉外部 requires，改从官方同版本 tarball 内置 tinyxml2 源码：配方内用 conf 编译器编成 `-fPIC` 静态库，`-I/-L` 经 AutotoolsToolchain 注入，`libtinyxml2.a` 随包发布供静态消费者链接（fastdds 有同类手动编译 tinyxml2 的先例；公共头不暴露 tinyxml2 类型） |
| 6 | 内置 tinyxml2 编译时 `conf.get("tools.build:compiler_executables:cpp", default=...)` 在真机抛 `[conf] ... does not exist` | `:子键` 直取形式在 conf 缺失时不回退 default（真机实证）；仓内已合入配方（fzy/faiss/2048.c）均为字典先取 | 改用 fzy/1.1 已合入模式：先取字典 `tools.build:compiler_executables`（default={}），再 `.get("cpp"/"ar")` 回退 `clang++`/`ar` |
| 7 | configure[137] 报 `/data/service/hnp/bin/bash: inaccessible or not found`（Error 127），上一轮编译器死路径修复后出现的新指纹 | 上一轮只修了 CC/CXX，本轮是同一 profile 的另一变量：`[buildenv] CONFIG_SHELL/SHELL` 仍指向已迁移的旧 HNP bash；autoconf configure 遇非空 CONFIG_SHELL 即 re-exec 自身，与编译器无关，故旧方案必然够不着 | zurl/1.12.0 notes #30（libdatovka 先例）adapt：`_resolve_shell` 永不复用 CONFIG_SHELL、优先 HMBS 保证的 /bin/sh；`generate()` 经 build-scope `hmbs_shell.sh` 覆盖 profile 值；configure 文件内硬编码 CONFIG_SHELL/SHELL（幂等 marker）+ 仅四种文件名 scrub；`build()` 前后各 scrub 一次 |
| 8 | 真机 compile 阶段 `sh: .../.harmonybrew/bin/rm: Out of memory`（2026-09-28 预检） | 全系统内存耗尽导致连 `rm` 都无法 fork；rarian 本体小，但默认 `-O2/-g` 编译+链接调试信息会放大编译器/链接器内存占用 | OHOS 限定加法式降载（不断言/测试开关不变）：`generate()` 内 `tc.cflags/cxxflags` 幂等追加 `-O1 -g0` + build-scope `hmbs_oom.sh` append 同组旗标；内置 tinyxml2 由 `-O2` 改为 `-O1 -g0`（保持 `-fPIC`）；`make -j1` 与 `--with-check` 不变 |
| 9 | 真机 `config.guess: unable to guess system type` → `configure: error: cannot guess build type`（2026-09-28 预检，config.guess 2023-06-23） | rarian 自带 GNU config.guess 无 HarmonyOS 分支，`uname -s`=HarmonyOS 直接落到 fail 分支；config.sub 亦不认 `linux-ohos` 三元组（E007/E072） | `build()` 新增幂等 `_patch_config_guess_sub_for_ohos`：遍历源码树全部 config.guess/sub，guess 补 `__OHOS__` LIBC 探测 + `*:HarmonyOS` → `*-unknown-linux-ohos` 分支，sub 补 `ohos-linux` 映射 + `ohos*` OS 白名单 + `linux-ohos*` 内核白名单；复刻 scripts/patch-autotools-ohos.pl 五处修改，不用 `--build/--host` 绕过 |
| 10 | 真机 `checking for tinyxml2... configure: error: no`（2026-09-28 预检；上一轮 config.guess 修复已生效，configure 进入依赖探测后倒下） | 上游 0.8.3 起改链系统 tinyxml2，configure 用 pkg-config 风格探针；内置私有库只有 `-I/-L` 工具链旗标、无 `.pc` 文件，且无 PkgConfigDeps 条目，探针必然报 no（与编译器无关；本仓 tinyxml2/11.0.0 自带 tinyxml2.pc 佐证） | `_build_vendored_tinyxml2` 在 configure 前向 generators_folder（已在 PKG_CONFIG_PATH 上）写最小 `tinyxml2.pc`（Version 11.0.0，与 conandata 内置 tarball 同版本）；`_build_environment` 追加 `CPPFLAGS/CFLAGS/CXXFLAGS(-I)`、`LDFLAGS(-L)` 并定义 `TINYXML2_CFLAGS/LIBS` 覆盖变量，多探针机制全覆盖；附带 diag 打印 lib/header/.pc 落盘证据 |

## 源码修改

无补丁（`patches_applied: []`）。首轮保持最小配方，由真机失败日志驱动后续补丁。

## 依赖版本

- tinyxml2 11.0.0（**源码内置**，非 requires：同版本官方 tarball 在配方内编成私有静态库，提供 `-ltinyxml2`；2026-09-24 预检证明 `requires tinyxml2/11.0.0` 会触发 conancenter 配方回退构建并在 OHOS 下失败，见问题 5）
- check/0.15.2（test_requires，仅上游 `make check` 用）
- pkgconf/3.0.5（tool_requires，提供 `PKG_CHECK_MODULES([CHECK], ...)` 所需的 pkgconf）
- libxslt 未引入：源码无 libxslt/libxml 链接引用；`xsltproc` 只是 `rarian-sk-extract` 脚本的运行时可选 helper，缺失时 configure 仅关闭 `ENABLE_EXTRACT`，不影响库与主工具。

## 验证结果

```bash
# 待 HMBS 真机预检（HarmonyOS aarch64）执行 conan create，日志将包含：
# HMBS_UPSTREAM_TEST_RESULT={"status":"...","framework":"automake",...,"discovered":29,...}
# HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,...}
```

- 本轮为首轮工作树，不猜测数字；PR 正文测试用例数留待真机 evidence 轮填写。
- test_package 用真实库 API（`rrn_info_get_categories` / `rrn_man_for_each` / `rrn_for_each` + shutdown 族），非空壳。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Autotools 配方：静态默认、--disable-skdb-update、tinyxml2 同版本源码内置静态编、私有 `-I/-L` 注入、make check 接入并输出 deterministric HMBS 标记 |
| conandata.yml | 官方 GitLab release URL + 实测 sha256（CI 无该域镜像映射，保留单 URL，不造假镜像）；tinyxml2 段复用本仓 tinyxml2/11.0.0 配方的官方 GitHub URL + sha256 |
| test_package/ | CMake 消费者测试：链接 librarian 并调用真实 API + 校验 rarian.pc |
| manifest.yaml | 版本元数据（交叉校验用） |

## 注意事项

- rarian 同时产出库（`librarian` → `lib/librarian.so|a`，pkg-config 名 `rarian`）与工具（`rarian-example`、`rarian-sk-*`），故软件级提供 `commands.json`（type tool 声明以满足 R38/L0k，库信息仍在 package_info）。
- 公共头要求先定义 `I_KNOW_RARIAN_0_8_IS_UNSTABLE` 再 `#include <rarian.h>`；test_package 已照此处理。
- 本轮严禁 commit/push/建 PR；工作树完成后即结束，由 HMBS 后台真机验证。
| 11 | 真机 util 链接报 __gxx_personality_v0/operator new/delete/__cxxabiv1 未定义（2026-09-29 预检，libtool --tag=CC 用 clang 链 rarian-example + librarian.a + -ltinyxml2） | librarian.a 与内置 libtinyxml2.a 含 C++ 对象（rarian-omf.cpp/tinyxml2.cpp），而 util 工具是 C 源码故 libtool 用 CC 驱动链接，不自动带 C++ 运行时 | generate() tc.ldflags 追加 -lc++（OHOS，profile libcxx=libc++，freeimage 设备实测 -lc++/-lstdc++ 均可）/-lstdc++（Linux）；_build_environment() 同值追加 LDFLAGS 并经 LIBS 保证静态归档后序；package_info system_libs 追加同名运行时，纯 C 消费者（含 test_package）可链静态库 |
| 12 | 真机 `make check` FAIL 1，conan 直接 Error 2 中断，上游标记缺失被判 incomplete（2026-09-29 预检） | `_run_upstream_tests` 对 `autotools.make(check)` 未做容错：automake 失败即抛异常，`check_rarian.log` 解析与 `HMBS_UPSTREAM_TEST_RESULT` 发射根本走不到；且 marker 不支持 gaps，失败用例名无证据留存 | `make check` 包 try/except（失败记 diag 不直接中断），沿用单一确定源 `check_rarian.log` 的 Checks/Failures/Errors 行计数，新增 `_collect_failure_evidence` 单遍抽 `:F:/:E:/Failure/Assertion` 行作证据，test-suite.log 尾部 diag 落盘，`_emit_upstream_marker` 新增 gaps 参数（failed>0 时 category=test_failure，数量恒等 failed），失败仍继续走完 marker 再按原逻辑处理 |
| 13 | mkdir EPERM preflight 2026-09-29 | harness mkdir EPERM OOM family; recipe overwrote HMBS TMPDIR | reuse injected TMPDIR/TMP/TEMP/HMBS_TMPDIR/HMBS_INSTALL/MKTEMP_FALLBACK, fallback build tmp; tests unchanged |
| 14 | config.status then SSH closed 2026-09-29 | configure passed to creating config.status, no recipe error; infra SSH drop. Tightened tmp to official vars only, dropped HMBS_INSTALL borrowing; tests unchanged |
| 15 | `make check` FAIL: `Error loading shared library libcheck.so` + srunner_* relocation failures, exit 127, no Checks line (2026-09-29 preflight) | check/0.15.2 test_requires lib dir not on loader path for `make check`; binary died before libcheck summary, marker fell back to skipped/unparseable | Scoped runtime env only for check (radvd/2.20 precedent adapt): `_dep_folder(check,lib)` across test/host/build contexts prepended to LD_LIBRARY_PATH + LD_PRELOAD to absolute libcheck.so on OHOS (HMBS stale_runtime_library diagnosis); configure/compile env untouched, no test skip, no count fixups |
| 16 | `make install` install-pkgincludeHEADERS Error 64 after 25/29 upstream pass (2026-09-29 preflight, 2nd fix round) | configure-probed INSTALL is HMBS runtime shim binary; its multi-source `install -c -m 644 h1 h2 ... dest` fails Error 64 on HMDFS (E596/libnih same fingerprint); 4 upstream man/info assertion failures are separate real test results, already honestly emitted as gaps | package() overrides INSTALL with tarball install-sh via `/bin/sh install-sh -c` (libnih multi-header success pattern); INSTALL_DATA/PROGRAM follow via ${INSTALL}; scoped to install only, no assertion/test-count changes |
| 17 | test_package CMake configure fails: CMAKE_C_COMPILER=/data/service/hnp/bin/clang dead path (2026-09-29 preflight, 3rd fix round; main build+install now pass) | test_package used declarative CMakeToolchain generators with no compiler resolve, so stale profile path flowed into conan_toolchain.cmake; same migrated-device fingerprint as main-recipe CC/CXX fix | test_package generate() now resolves usable c/cxx (conf when executable else PATH else ~/usr/local/bin), pins CMAKE_C/CXX_COMPILER cache vars, rewrites conan_toolchain.cmake in place and exports CC/CXX (zydis/4.1.1 test_package adapt); no test-count changes |
