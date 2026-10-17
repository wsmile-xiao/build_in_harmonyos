# cvechecker 4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-29
- 编译器: clang/clang++ (OHOS aarch64, /data/service/hnp)
- 状态: built（配方已就绪；真机 rule4 预检尚未在本轮执行）

## 源码信息
- 上游仓库: https://github.com/sjvermeu/cvechecker（作者 sjvermeu，2020-07 发布 4.0，项目已归档）
- 版本: 上游 release tag = `cvechecker-4.0`；本配方 conan 版本号取 `4`（与分支 feat/cvechecker-4、PR 标题一致）
- 源码 URL: https://github.com/sjvermeu/cvechecker/archive/refs/tags/cvechecker-4.0.tar.gz
- SHA256: `d48b4c1976d866f6cf493340dc48e4c2b67d2394b6b5467ddc760b0f82466c4d`
  - 本地沙箱无法直连 GitHub，故经代理取回该官方 archive，**用发行版打包方（BlackArch/Gentoo-liguros）发布的权威 SHA512 `c24aa1e6...` 交叉核验字节一致**后再计算 SHA256；文件大小 419915 字节一致。

## 构建系统分析（自举必需）
- configure.ac 采用 Autotools：`AC_INIT([cvechecker],[4.0])`、`AM_INIT_AUTOMAKE([subdir-objects foreign])`、`AC_CONFIG_HEADERS([config.h])`、`AC_CONFIG_FILES([Makefile src/Makefile data/Makefile conf/Makefile scripts/Makefile docs/Makefile])`。
- **GitHub archive 只是 git 快照**：tar 包内含 `configure.ac` 与已提交的 `configure`、`depcomp`、`install-sh`、`missing`，但**没有** `Makefile.in` / `aclocal.m4` / `config.h.in`。已提交的 `configure` 因缺 `Makefile.in` 无法被 AC_CONFIG_FILES 使用，因此配方在 configure 前必须 `autoreconf -fi` 自举（同仓库 argp-standalone/1.5.0 的既有做法）。
- configure 硬性依赖（PKG_CHECK_MODULES / AC_CHECK_HEADERS）：
  - `libbsd`（无条件 `PKG_CHECK_MODULES([BSD],[libbsd])`）
  - `libconfig >= 1.3`（`PKG_CHECK_MODULES([CONFIG],[libconfig])`）
  - `sqlite3 >= 3.6.16`（默认开启，`--enable-sqlite3`）
  - `argp.h`（`AC_CHECK_HEADERS([argp.h])`，OHOS musl libc 无 argp，需 argp-standalone）
  - mysql 为可选（`--enable-mysql`，未启用）

## 上游测试审计（上游无测试）
- 直接审计 cvechecker-4.0 源码树与全部 Makefile.am：无 `tests/`、无 `TESTS=`/`check_PROGRAMS` 目标。
- Alpine 4.0 官方构建日志实证：`make check` 在每个子目录均输出 "Nothing to be done for 'check'"。
- 结论：上游确无自动化测试 → `test_package/MANIFEST.yml` 置 `upstream_tests_exist: false` 并附 `upstream_test_audit`；本次以 test_package 对打包二进制做消费端冒烟验证，不冒充上游覆盖。

## 依赖（Requires）
- `libconfig/1.7.3`（制品仓已有，配置库，pkg_config_name=libconfig）
- `sqlite3/3.53.4`（制品仓已有，pkg_config_name=sqlite3；默认后端）
- `argp-standalone/1.5.0`（制品仓已有 recipe；argp.h + libargp.a，非 pkg-config；配方显式注入其 include/lib 路径并 -largp）
- `libbsd`：**不列入 requires**。真机 preflight 证据：`ERROR: Package 'libbsd/0.11.7' not resolved: Unable to find 'libbsd/0.11.7' in remotes. Required by 'cvechecker/4.0'` —— libbsd 在 ohpcd 与 conancenter 均无发布。cvechecker 的 configure.ac 无条件 `PKG_CHECK_MODULES([BSD],[libbsd])`，且源码仅使用其 `strlcpy`（`cvecheck_common.h`/`output/stringscmd.h` 各 `#include <bsd/string.h>`，OHOS musl libc 无 strlcpy）。配方改为在构建期合成最小 vendored libbsd（见「遇到的问题与解决方案」#6）。

## 构建步骤（配方内）
1. `get()` 拉取源码
2. `_build_vendored_libbsd()`——合成最小 vendored libbsd：真实 `strlcpy` 编译为 libbsd.a、写 `<bsd/string.h>`、把 libbsd.pc 放入 generators 目录（已在 configure 的 PKG_CONFIG_PATH 上）
3. 手动 autotools 自举（aclocal → autoconf/autoheader → automake，均经 conan perl 解释器驱动：aclocal/automake 用 `<conan auto>/bin/.aclocal-real/.automake-real`，autoconf/autoheader 用 `<conan auto>/bin/autoconf|autoheader`；见「遇到的问题与解决方案」#7，不用会崩的 HNP autoreconf/autoconf）
4. `./configure --enable-sqlite3`（PkgConfigDeps + VirtualBuildEnv 使 libconfig/sqlite3 的 .pc 被 PKG_CHECK_MODULES 发现；vendored libbsd.pc 满足无条件的 `PKG_CHECK_MODULES([BSD],[libbsd])`）
5. `make -j1`
6. `make install`
7. 无 `make check`（上游无测试）


## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub archive 无 Makefile.in | 快照不含生成产物 | build() 先 `autoreconf -fi` |
| 2 | configure 找不到 argp.h/链接 argp | OHOS musl 无 argp | requires argp-standalone，注入 include/lib 并 -largp |
| 3 | 依赖发现 | PKG_CHECK_MODULES | PkgConfigDeps + VirtualBuildEnv 提供 .pc |
| 4 | libbsd 无 conan 配方 | 仓库仅元数据，status=built | 曾列入 requires；真机 PF4 证实图解析硬失败（见 #6） |
| 5 | 真机 rule4 预检 compile 失败：`Exporting recipe to the cache` → `ERROR: Invalid package version '4'` | 任务头版本固定单字符 `4`，Conan 2.29 RecipeReference 校验版本最短 2 字符，导出阶段即拒 | 沿用仓库 set_version() 目录-制品分离方案（cronic/3→v3、ndpi/5→5.0）：目录/分支/白名单保持 `4`，conanfile.py 去掉字面 `version="4"`，改 `set_version()` 返回上游点号形式 `4.0`（AC_INIT [cvechecker],[4.0]，tag cvechecker-4.0），产物为 `cvechecker/4.0` |
| 6 | 真机 preflight compile 失败：`ERROR: Package 'libbsd/0.11.7' not resolved: Unable to find 'libbsd/0.11.7' in remotes. Required by 'cvechecker/4.0'` | libbsd 在 ohpcd 与 conancenter 均未发布，`self.requires("libbsd/0.11.7")` 使 Conan 图解析在依赖解析阶段硬失败；而 cvechecker 源码实际上只依赖 libbsd 的 `strlcpy`（OHOS musl libc 亦无 strlcpy） | 从 requirements() 移除 libbsd；新增 `_build_vendored_libbsd()`：构建期合成最小 vendored libbsd —— 真实 `strlcpy`（非 no-op，cvechecker 字符串处理依赖其语义）经 profile 的 CC 编译为 `libbsd.a`、写入 `bsd/string.h`、把 `libbsd.pc`（`-I<stub>/include -L<stub>/lib -lbsd`）放到 generators 目录使 configure 的 `PKG_CHECK_MODULES([BSD],[libbsd])` 与 `$BSD_LIBS` 链接均可解析；`generate()` 经 `tc.extra_cflags` 注入 `-I<stub>/include`（configure.ac 只把 `$CONFIG_CFLAGS` 并入 CFLAGS、从不并入 `$BSD_CFLAGS`，故需显式加 -I）。这是对仓库既有「vendored no-op stub 替代未发布依赖」模式(#242)的**适配**：本库 strlcpy 必须为真实实现而非 no-op |
| 7 | 真机 preflight compile 失败 x2：①`Can't load '.../conan perl .../auto/Cwd/Cwd.so' ... Error relocating ...: Perl_my_cxt_init: symbol not found at /data/service/hnp/bin/autoreconf line 48`；②`RUN: autoconf --force` → 同样 `Can't load .../Cwd.so: Perl_my_cxt_init: symbol not found at /data/service/hnp/bin/autoconf line 44` | 双 perl 解释器陷阱（知识 E729）：`build_requirements` 的 `perl/5.42.2` 使 conanbuild 的 `PERL5LIB` 指向 conan perl 5.42.2 的 XS 目录，而 bare 命令（autoreconf/autoconf）仍经 PATH 解析到 `/data/service/hnp/bin` 的 HNP perl 5.42.0（非 i-thread）；HNP perl 无 `Perl_my_cxt_init` 符号，加载 conan 的 `Cwd.so` 时 relocation 失败 | 不再调用 `autotools.autoreconf()`；改为手动自举 `aclocal(.aclocal-real) → autoconf/autoheader → automake(.automake-real)`，aclocal/automake 经 `perl -I automake_share <conan>/bin/.aclocal-real/.automake-real` 驱动；**本轮修复 autoconf/autoheader 同样经 `perl <conan_autoconf>/bin/autoconf` / `perl <conan_autoconf>/bin/autoheader` 用 conan perl 驱动**（此前这二者误用 bare 命令解析到 HNP perl 而崩溃），其余可重定位参数（`--automake-acdir/--system-acdir/--libdir`）、`share/automake-1.18` 放 `-I` 与仓库 abx 配方同构；`_autotools_perl()` 在 build 图里确定性解析 conan perl 路径；generate 追加 HNP `share/aclocal` 到 `ACLOCAL_PATH`（供 pkg.m4 的 PKG_CHECK_MODULES）并设定可写 TMPDIR |
| 8 | 真机 preflight compile 失败：跑到 `configure` 时 `configure: error: working directory cannot be determined`，前面大片 `shell-init: error retrieving current directory: getcwd: cannot access parent directories: <errno>` / `pwd: error retrieving current directory: getcwd: ...` errno 风暴 | 深 conan 构建目录（HMDFS）里运行的 shell 的 `getcwd()` 失败（HNP bash 5.3 对整棵 HMDFS 树 getcwd 失败，知识 E386/cvsgraph/classads/oscats 同款）。autoconf 生成的 configure 在 `_AC_INIT_DIRCHECK` 里做 `ac_pwd=\`pwd\` && test -n "$ac_pwd" && ... || AC_MSG_ERROR([working directory cannot be determined])`；`pwd`（内建/命令）因 getcwd 失败返回空/非零即中止 | 三管齐下（均仓库既有先例）：① `generate()` 的 AutotoolsToolchain 环境注入 `SHELL`/`CONFIG_SHELL=/system/bin/sh`（cvsgraph 1.7.0 真机实证的 getcwd 干净 toybox sh）；② `build()` 在 bootstrap 后、`autotools.configure()` 前调 `_patch_configure_for_ohos()`：把刚由 autoconf 2.72 生成的 `configure` 里 `ac_pwd=\`pwd\`` 替换为 `ac_pwd=\`pwd 2>/dev/null || echo "<build_folder_abs>"\``（回填真实构建目录绝对路径，lightning/2.2.3 经验 #1 同款；`||` 在 `pwd` 失败时兜底，ac_pwd 必非空），并把 `umask 077` → `umask 022`（HMFS config.status 临时目录 E011 族）；③ `build()` 顺手 `os.environ["PWD"]=<build_folder>`（libuio/cvsgraph 逻辑 pwd 方案，让 bash 走 stat 校验的 PWD 而不依赖 getcwd）。configure 每次由 autoconf 重生成，故补丁必须在每次 bootstrap 之后、configure 之前执行 |
| 9 | 真机 preflight compile 失败：编译通过后 `package()` 的 `autotools.install()` 在 `install-cvecheckerDATA` 报 `make[2]: *** [Makefile:292: install-cvecheckerDATA] Error 64`，命令为 `.../bin/install -c -m 644 <data/cvereport.xsl report.css csv2xml.awk mysql_cvechecker.sql> '<dest>/share/cvechecker'` | E182/E188（adms 2.3.7 / aribb24 1.0.4 / cdecl / cubelib 4.9.1 同款）：真机 HMBS/toybox `install` shim 只接受单源形式，多源拷贝到目录（`install -c -m 644 f1 f2 ... dest/`）退出 64（EX_USAGE）；且 `-m 644` 依赖 chmod，但 `HMBS_CAP_CHMOD=0` 不支持。`install-cvecheckerDATA` 用 `$(INSTALL_DATA)`（configure 烘焙为绝对 `<...>/install -c -m 644`），拷 4 个 data 文件时必挂 | 仿 cubelib 4.9.1（已过门禁）在 conanfile 新增 `_write_install_shim()`（cp/mkdir 多源 shim，`-c/-m/-d/--` 全解析、逐个 `cp -f`、chmod 容错跳过，`os.open 0o755` 生成可执行）与 `_redirect_install_to_shim()`（遍历 build_folder 下所有生成 Makefile，把引用了 `/install` 的 `INSTALL/INSTALL_DATA/INSTALL_PROGRAM/INSTALL_SCRIPT` 四变量改写指向 shim）；`package()` 在 `autotools.install()` 前写 shim 并重定向（build() 的改写随构建树保留，但 package() 可能独立运行故需双保险）。不动上游测试、不删断言。本机已完成 py_compile 语法校验 |
| 10 | 真机 preflight test_package 失败：**incomplete（缺少 test_package 真实用例计数和机器测试证据）**；上游测试 发现0/执行0/通过0；但 stdout 尾部已出现 `cvechecker smoke test: OK (argp usage reached)` —— 说明冒烟脚本真跑了且二进制可执行，只是旧 `test_cvechecker.sh` 仅 1 条 grep 断言、且 `test_package/conanfile.py` 未输出 HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT 机器证据标记 | 门禁要求 test_package 必须有真实用例计数与机器测试证据标记；旧脚本单断言且依赖 grep "Usage" 判定（只有 PASS/FAIL 二进制结果，无确定性计数）；conanfile 的 test() 仅 `self.run("sh test_cvechecker.sh ...")` 不产出任何 HMBS 标记，故判 incomplete | 仿 c10t/1.7（已过门禁）改：① `test_cvechecker.sh` 改为 4 条真实断言的消费者功能测试（C1 `--help` 退出 0；C2 `--help` 输出非空；C3 `--help` 输出含 argp 'Usage'；C4 负向对照——未知长选项必被 argp 拒绝，证明 harness 能抓真失败），末尾打印确定性 `RESULT: P passed, F failed` 行；② `test_package/conanfile.py` 的 test() 把脚本输出重定向到日志、用正则解析 RESULT 行得真实 discovered=passed+failed, passedCount=passed，输出 `HMBS_TEST_PACKAGE_RESULT`，并输出 `HMBS_UPSTREAM_TEST_RESULT({"status":"no_tests",...discovered:0,executed:0...})`（上游无测试，见 MANIFEST 审计）；workspaces 用 HMBS 注入的 TMPDIR/TMP/TEMP（HMFS /tmp 只读）；③ MANIFEST 更新 4 条断言说明。不失真、不伪造计数：discovered/passedCount 唯一来源即脚本真实 RESULT 行 |
| 11 | 真机 preflight evidence 失败：incomplete（rule4：必须声明合法的 upstream_test_total，缺失不能按 0 处理）；上游测试 发现0/执行0/通过0，HMBS_UPSTREAM_TEST_RESULT(status=no_tests) 已输出但被门禁拒绝 | rule4 证据自洽（DRAFT-udt-4.11 经验 #2265 同款）：test_package/MANIFEST.yml 作为 CI L0e 机器可解析声明文件，即便上游确无测试，也必须**显式声明** upstream_test_total；当前 MANIFEST 只写 upstream_tests_exist:false + 审计，缺 upstream_test_total 字段，缺失按 0 处理会被 rule4 直接拒绝 | 已在 test_package/MANIFEST.yml 现声明显式补 upstream_test_total: 0 + upstream_test_count_method: autotools_tests（+passed/failed/skipped 均 0）。cvechecker 4.0 上游经完整审计（GitHub cvechecker-4.0 递归 tree 复位确认：根与 src/data/conf/scripts/docs 全部 Makefile.am 均无 TESTS/check_PROGRAMS，源码树无任何测试文件）确认确实没有自动化测试，故 no_tests 口径为真、总数=0 合法（区别于“缺失按 0 处理”）。不注入合成 make check：那会伪造上游不存在的测试，违背守则 no_tests 显式审计路径 |

## 源码修改
无补丁（配方未改动上游源码）。libbsd 通过 build() 内生成的 vendored `<bsd/string.h>` 头 + 真实 `strlcpy` 实现（见 _build_vendored_libbsd）满足，不入 requires、不改上游代码。

## 验证结果
- 真机 rule4 evidence 预检已反馈：编译/test_package 均通过，仅 evidence 阶段因 `upstream_test_total` 未显式声明被 rule4 拒绝（缺失不能按 0 处理）。
- 本轮修复：`test_package/MANIFEST.yml` 显式声明 `upstream_test_total: 0`、`upstream_test_count_method: autotools_tests` 及 passed/failed/skipped 均 0。等待 HMBS 复跑真机预检确认 evidence 放行。
- 真机通过后回填 conan create / make check / test_package 实测数字。

## 注意事项
- libbsd 已通过 vendored mini-libbsd（真实 strlcpy + libbsd.pc）解决，不再依赖任何 libbsd conan 包；configure 无条件的 `PKG_CHECK_MODULES([BSD],[libbsd])` 与 `$BSD_LIBS` 链接由 vendored 产物满足。
- argp-standalone 的 pkg-config 注入为经验性写法（上游非 pkg-config 模块），若 configure/make 链接阶段有出入，以真机日志为准微调。
- 本仓库上游 main 含一个文件名结尾带 `\r\r` 的坏文件（archives/g/gama/...），Windows 本地无法完整检出上游树；本任务已用 sparse-checkout（排除 archives/g）完成配方文件工作，不影响真机（Linux 加载器可处理）。
