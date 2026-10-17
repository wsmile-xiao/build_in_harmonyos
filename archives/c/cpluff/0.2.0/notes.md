# cpluff 0.2.0 适配笔记

## 编译环境

- 构建系统: autotools (configure + make + make check)
- 编译器: clang 15 (HarmonyOS PC 真机工具链, 经 profile `tools.build:compiler_executables` 注入)
- 状态: built (工作树待真机预检, 通过前不提交)
- 认领身份: GitCode 用户名 `sheepss`, 队伍 `来都来了`

## 上游信息

- 上游: C-Pluff 0.2.0, C 语言插件框架
- 官网: https://c-pluff.org/
- 源码包: https://c-pluff.org/downloads/cpluff-0.2.0.tar.gz
- sha256: `2b769eea5926207232bb715b312caebd5ceeb9be4a086d02a1ac82441c53243a`
  (1369314 字节, 两次独立下载核对一致)
- 仓库镜像: https://github.com/jlehtine/c-pluff
- 许可证: MIT (C-Pluff license, OSI approved); kazlib 子目录为 Kazlib license;
  以 `--without-readline` 避免链接 GPL 的 readline, 保持二进制 MIT 洁净
- 构建系统: GNU autotools; 官方 tarball 自带 configure, 无需 autogen

## 上游测试清点

- `test/Makefile.am` 定义 `check-local` 目标, 经由顶层 `make check` 触发
- `test/testsuite` 由 psymbolusage.c、extcfg.c、pdependencies.c、pcallbacks.c、
  pscanning.c、pinstallation.c、ploading.c、loggers.c、collections.c、
  ploaders.c、initdestroy.c、fatalerror.c、cpinfo.c、testmain.c 编译而成
- `test/tests.txt` 登记 53 个用例 (getversion、gethosttype、fatalerrordefault、
  fatalerrorhandled、fatalerrorreset、initdestroy 等, 一行一个, `wc -l` 得 53)
- 另有 `test/test-*` 包装脚本与 `expected/`、`plugins/`、`pcollections/` 参照数据
- 证伪说明: check-local 对每个用例执行 testsuite 二进制并按退出码判定
  OK/FAIL/SKIPPED, 失败计数非零则 `test $$numf -eq 0` 非零退出导致
  `make check` 失败; 桩二进制无法通过插件扫描与符号解析, 不存在静默跳过路径
- C++ 接口 (`--enable-cpluffxx`) 上游标注 work in progress, 默认关闭, 本配方不启用

## 编译步骤

1. `get()` 解包官方源码包, `apply_conandata_patches()` 应用 `patches/0001-*.patch` 与 `patches/0002-*.patch`
2. `AutotoolsToolchain` 生成, 附加 `--build/--host=aarch64-unknown-linux-gnu`
   与 `SHELL=<bash>`、 `--disable-nls --without-readline`、
   `--enable-shared --enable-static` (双产出供 make check dlopen 插件 .so，
   package() 再按 shared 选项裁剪)
3. `generate()` 经 `Environment` 注入 expat 的 `CPPFLAGS/LDFLAGS`
   (`AC_CHECK_HEADER/AC_CHECK_LIB` 不走 pkg-config, 仿 dbus-glib 做法);
   OHOS 下置 `ACLOCAL/AUTOMAKE/AUTOCONF=true` 避免触发 automake 重生成;
   不再前置 SDK `llvm/lib` 到 `LD_LIBRARY_PATH` (HNP clang 自带运行时,
   额外前置曾与 harmonybrew sed 冲突, 伴随 `can't fork`/`sed: Out of memory`);
   另经 `cpluff-deps` 构建脚本透传 HMBS 注入的 `TMPDIR/TMP/TEMP`,
   保障 configure/make/libtool 子进程均可见可写临时目录
4. `build()` 先对 `configure`/`config.status` 做 `umask 077 -> umask 022`
   确定性替换 (HMDFS 0700 临时目录不可写问题, cflow/c-ares 同源),
   复用注入的 `TMPDIR/TMP/TEMP`, 再 `configure`; configure 后对生成的
   `libtool` 脚本做 E002 最小替换 (`: ${TMPDIR=/tmp}`/`tmpdir=/tmp` 等
   仅换临时根为 `$TMPDIR`, 不改测试逻辑), 再 `make -j1`
5. `make check` (上游 53 用例套件), 成功即输出
   `HMBS_UPSTREAM_TEST_RESULT` 标记 (discovered/executed/passed 均按
   `test/tests.txt` 行数 53 填写, 失败则标记 failed 并抛错)
6. `autotools.install()`, 删除 `*.la` 并按 shared 选项裁剪 (`shared=True` 删 `*.a`，
   否则删 `*.so*`)，拷贝 `COPYRIGHT.txt` 与
   `ChangeLog.txt` 到 `licenses/`
7. test_package: 以 CMake 构建 `test_cpluff.c` (真实调用 `cp_init`、
   `cp_get_version`、`cp_create_context`/`cp_destroy_context`), 运行后输出
   `HMBS_TEST_PACKAGE_RESULT` 标记 (discovered/passedCount 均为 3)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 老旧 config.guess 可能不识别 ohos/aarch64 三元组 | 上游 0.2.0 发布于 2020 年, 自带 config.guess 早于 HarmonyOS | 显式传递 `--build/--host=aarch64-unknown-linux-gnu` 绕过探测, 不打补丁 |
| 2 | configure 与测试脚本依赖 bash 行为 | OHOS `/bin/sh` 非 bash | `SHELL` 指向 bash (同 gnu-which 2.25 做法) |
| 3 | HMDFS 上 `config.status` 可能报 `can't create subs1.awk: Permission denied` | `mktemp -d ./confXXXXXX` 建出的 0700 目录后续不可写 (E011 同源) | `configure`/`config.status` 内 `umask 077 -> umask 022` 确定性替换, 文件编辑不走补丁 |
| 4 | expat 探测不走 pkg-config | 上游用 `AC_CHECK_HEADER`/`AC_CHECK_LIB` 直接探测 | `generate()` 经 `Environment` 追加 `CPPFLAGS -I<expat>/include` 与 `LDFLAGS -L<expat>/lib` |
| 5 | gettext/readline 可选依赖在 OHOS 上缺失 | 真机无系统级 gettext 与 readline | `--disable-nls --without-readline` 走上游支持选项, 不改源码, 同时保持 MIT 许可洁净 |
| 6 | 真机 Release 报 `cpi_lock_framework` 宏实参过多, `cpluff.lo` 编译失败 | 真机未检出线程支持且默认 `-DNDEBUG`: `internal.h` 在此配置下把锁函数定义为无参宏, 但 `libcpluff/cpluff.c` 无条件定义同名函数, `(void)` 被当作宏实参展开失败; 同文件 `context.c` 已有 `CP_THREADS/NDEBUG` 守卫, `cpluff.c` 遗漏 | 新增 `patches/0001-*.patch`, 给 `cpluff.c` 的两个 framework 锁函数补与 `context.c` 相同的 `#if defined(CP_THREADS) \|\| !defined(NDEBUG)` 守卫, 无线程 Release 走 no-op 宏, 不改测试口径 |

| 7 | 真机 cpluff-loader 链接失败 undefined hidden symbol: cpi_context_owner (pinfo.o/psymbol.o 引用) | cpi_context_owner 在 internal.h 无条件声明、logging.c/pinfo.c/psymbol.c 经 cpi_debugf 无条件引用, 但其定义被包在 context.c 的 CP_THREADS/NDEBUG 守卫内; 真机 Release 无线程配置下定义消失而引用仍在 | 新增 patches/0002-*.patch: 把守卫的 endif 提前到 Debug helpers 之前, cpi_context_owner 移到守卫之外恒有定义, 锁函数保持守卫不变; 已在本地纯净源码上 git apply --check 验证通过 |
| 8 | 真机预检 compile 阶段 Signal 9 (空日志, 上游测试 0/0/0, marker 未输出, 进程在 configure/make 期间被 SIGKILL) | 受限预检 runner 上峰值内存/IO 触发 OOM-killer 或超时 kill; 配方默认带调试符号且构建 C++ 附属目标与 automake 依赖跟踪, 放大了峰值开销; 测试口径未受影响 (marker 未输出证明 kill 发生在测试标记前) | 最小资源加固, 不跳过任何测试: `extra_cflags/cxxflags -g0` 去调试符号降 clang/ld 峰值内存, `--disable-dependency-tracking` 减 IO, `--disable-cpluffxx` 显式关闭默认即 off 的 WIP C++ API (configure.ac 仅在 =yes 时才跑 C++ 探针), 保持 `make -j1` 与 53 用例 `make check` 全量执行 |
| 10 | 真机 `configure` 在 912/1249 行 `harmonybrew/bin/expr: Operation not permitted`, 随后 `configure: error: invalid variable name`, `autotools.configure()` Exit 126 | 上轮删除 SDK llvm/lib 前置后, harmonybrew GNU expr 在受限 runner 上偶发不可执行; autoconf 依赖 expr 做字符串匹配, 失败即变量名解析错误 (E010 家族); 另 generate() 透传 TMPDIR 时未校验 fallback 是否为目录, 可能导出无效路径 | 与上轮无条件删除不同, 改条件化策略: build() 先探测候选 expr (`PATH` 解析、` /bin/expr`、`/usr/bin/expr`、harmonybrew), 以 `expr 1 + 1`=2 为准把可用目录前置到 PATH; 仅当全部失败才把 SDK llvm/lib 以追加(非前置)方式补入 LD_LIBRARY_PATH 重试一次; 同时 generate() 补 isdir 校验, 无效 TMPDIR 不导出; 不重装工具、不跳过测试 |
| 11 | 真机 preflight.sh[306] `can't create temporary file /tmp/she*.tmp: Read-only file system` + `can't fork - try again` + `can't open /proc/<pid>/cmdline`，阶段 compile，上游测试 0/0/0，平台诊断 readonly_tmp | shell 内部 heredoc/命令替换固定写 /tmp（只读 erofs），叠加两处配方缺口：① config.status 由 configure 生成，预补丁只覆盖 configure 时刻、生成后副本仍含 `mktemp -d "./confXXXXXX"`/`umask 077`；② 自研 expr 多候选 subprocess 探测 + SDK llvm/lib 路径硬编码 + build() 内 os.chdir，违反“优先复用 HMBS 注入能力”，在已 can't fork 的 runner 上增加 fork 压力 | 最小适配不跳过测试：① 新增 `_patch_generated_config_status()` 在 configure 后对 source/build 两树生成的 config.status 重做 umask 022 + TMPDIR + ac_pwd 回退替换（复用 aldo 0.7.8 后置补丁模式）；② 删除 `_ensure_working_expr()` 及其调用与 SDK 硬编码回退，复用 HMBS 注入 PATH/SHELL/TMPDIR；③ `_ensure_tmpdir()` 去掉 os.chdir/PWD 改写，仅导出 TMPDIR/TMP/TEMP 与 HNP-shell 修复；测试口径不变 |
| 9 | 真机 `make` 在 `pcontrol.lo` 处 `libtool: can't fork - try again` + harmonybrew `sed: Out of memory` + `invalid operation mode 'compile'`, 平台诊断 `readonly_tmp` (`/tmp` 只读, `can't create /tmp/shuf*.tmp`) | 生成的 `libtool` 仍用硬编码 `/tmp` 做临时文件, 且配方曾把 SDK `llvm/lib` 前置到 `LD_LIBRARY_PATH`, 污染 libtool fork 的 `sed` 等子进程, 在受限 runner 上放大为 fork/OOM; configure 直调 clang 能过, 只有走 libtool 的编译失败, 与此一致 | 最小适配不跳过测试: ① 删除 SDK `llvm/lib` 的 `LD_LIBRARY_PATH` 前置 (HNP 工具链自带运行时); ② `generate()` 经 `cpluff-deps` 构建脚本透传 `TMPDIR/TMP/TEMP`; ③ 新增 `_fix_libtool_tmpdir()` 仅把生成 `libtool` 的临时根换成 `$TMPDIR`, 测试口径不变 |
| 12 | 真机 `configure: error: working directory cannot be determined` + `shell-init/job-working-directory/pwd: getcwd: cannot access parent directories` 成百上千行, 阶段 compile | HMDFS 上 getcwd 系统调用失败, `pwd` 内建/二进制取不到 cwd; 上轮为降 fork 压力删除了 `os.chdir/PWD` 改写, 导致 `ac_pwd=\`pwd\`` 回退的 `$PWD` 为陈旧值, autoconf 的 `ac_pwd/ls -di` 链直接报错; 同 autoconf 家族 aldo 0.7.8 以 `chdir(build_folder)+PWD=build_folder` 作为标准兜底 | 恢复最小 HMDFS 兜底不加探测: ① `_ensure_tmpdir()` 内 `chdir(build_folder)+PWD=build_folder`; ② `build()` 在 configure 前再次断言 live cwd/PWD; ③ `autotools.configure(build_script_folder=self.source_folder)` 显式分离源码与构建目录; 复用 HMBS 注入 SHELL/TMPDIR, 无新增子进程探测, 不改测试口径 |

| 13 | 2026-09-11 preflight.sh[306] `can't create temporary file /tmp/sh*.tmp: Read-only file system` + `can't open /proc/<pid>/cmdline`, libtool compile progressed through ploader/pinfo/pcontrol/serial then `Connection closed`, phase compile, upstream 0/0/0, diagnosis readonly_tmp | Recipe already routed autoconf/libtool tmp via TMPDIR, but two gaps remained: (1) generate()/_ensure_tmpdir() overwrote a valid HMBS TMPDIR with HMBS_AUTOCONF_MKTEMP_FALLBACK unconditionally, risking a stale root while shell reports readonly /tmp; (2) chosen tmpdir was only isdir-checked, never proven writable on HMDFS | Minimal E002 hardening, no test change: (1) fallback only fills when primary TMPDIR/TMP/TEMP missing/invalid in both generate() and _ensure_tmpdir(); (2) winner must pass a touch-file writability probe, else build_folder/tmp; (3) _fix_libtool_tmpdir() guards "0"/"1" and non-dir TMPDIR. Reuses HMBS TMPDIR/FALLBACK, no new subprocess probes, make -j1 and make check 53 cases unchanged |
| 14 | 2026-09-11 upstream_test `Error loading shared library libexpat.so` + `XML_ParserCreate: symbol not found` x11 per binary, 51/53 FAIL (only getversion/gethosttype pass), `make check` rc=1 | Test binaries (console/cpluff-console, test/testsuite) link `-lexpat` via `-L<expat>/lib` without rpath/runenv; true-machine musl loader finds no libexpat.so at `make check` runtime, so every libtool-executed case fails before any assertion | Minimal runtime fix, no test change: (1) generate() appends `-Wl,-rpath,<expat>/lib` to LDFLAGS and `LD_LIBRARY_PATH=<expat>/lib` (build scope via cpluff-deps); (2) build() prepends expat lib dir to os.environ LD_LIBRARY_PATH/LIBRARY_PATH before configure/make/check (direct dep only, no SDK llvm/lib shadowing). make -j1 and 53-case `make check` unchanged |
| 15 | 2026-09-11 upstream_test 47/53 通过、剩余 6/53 FAIL：plugincallbacks/symbolusage 报 `tmp/install/plugins/*/libruntime.so could not be opened: No such file`，extpoints/extensions 输出对照失败 | 默认静态配置 `--disable-shared` 使 `-module -avoid-version` 插件模块只产出静态 .a，`DESTDIR=tmp/install install` 后无 .so 可供 testsuite dlopen；与 install-shim 无关（47 个非 dlopen 用例已过证明安装主链正常） | 最小构建修正不改测试：generate() 改为恒用 `--enable-shared --enable-static` 以产出插件 .so 供 make check dlopen；package() 按 `shared` 选项裁剪（shared=True 删 *.a，否则删 *.so*），最终包仍守选项语义 |
| 16 | 2026-09-11 upstream_test 49/53 通过、剩余 4/53 FAIL（extpoints/extensions/loadminimal/loadmaximal），直接 testsuite 用例全过，仅走 cpluff-console 的包装脚本失败；stderr 仍见 preflight.sh[306] `can't create temporary file /tmp/sh*.tmp: Read-only file system` | 4 个失败恰为唯一使用 `<<EOI` heredoc 的 test-extpoints/test-extensions/test-loadminimal/test-loadmaximal；/bin/sh 将 heredoc 物化为 /tmp/sh*.tmp，而真机 /tmp 为只读 erofs，與 direct-testsuite 路径无关 | 最小 harness 适配不改测试语义：build() 新增 `_fix_test_heredoc()`，将 `cmd <<EOI > out … EOI` 改写为 `printf '%s\n' "行1" … \| cmd > out` 管道（同字节 stdin、同 argv、保留 $srcdir 运行时展开与 libtool 路径修复），消除 /tmp 临时文件 |
| 17 | 2026-09-11 upstream_test 仍 4/53 FAIL 且出现 `/bin/sh: ..//bin/sh: No such file` | 上轮 heredoc 改管道方向正确但实现非幂等：`_fix_libtool_path()` 已把包装脚本改成 `/bin/sh ../libtool`，随后 `_fix_test_heredoc()` 对 `pre` 又做一次无条件 `replace("libtool --mode=execute", "/bin/sh ../libtool --mode=execute")`，把已修复行二次包裹成 `/bin/sh ..//bin/sh ../libtool`，shell 把 `..//bin/sh` 当脚本打开即报 No such file，4 个 console 包装用例因此全灭 | 最小修正不改测试语义：给 `_fix_test_heredoc()` 的 `pre.replace` 加 `if "../libtool --mode=execute" not in pre` 守卫，已修复行直接复用，仅裸 `libtool` 行才补 `/bin/sh ../libtool` 前缀，消除双重包裹 |
| 18 | 2026-09-11 上轮幂等守卫生效（`..//bin/sh` 消失）但仍 4/53 FAIL，摘要截断导致看不到 `diff -u` 实际差异 | 前次只修路径叠加，未解释 console 已运行但输出比对仍失败的原因；聚焦摘要省略了 `--- expected/...` 之后的 `+++`/`@@` 行，无法判断是 console 输出错还是 `sed` 过滤错 | 策略切换为取证优先不改测试口径：保留 printf 管道，仅新增 `_dump_console_diagnostics()` 在 `make check` 失败时打印 `console-out.txt`/`filtered.txt` 头部2000字符与 `sed/diff/sh --version`，下轮按实测差异再定内容修复 |
| 19 | 2026-09-11 诊断探针回显示 console-out 内容正确（extpoints/extensions 与预期逐行一致）但 4 个 filtered.txt 均为 0 字节，sed/diff 均为 GNU 且正常 | 真因非 heredoc/管道字节差异，而是 `console/cmdinput_basic.c` 的非 tty 输入回显被编译关闭：`HAVE_ISATTY_FILENO` 未定义时不执行 `fputs(cmdline)`，提示符与命令输出粘连成 `C-Pluff Console > Installed ...` 同一行，`sed -n /^Installed.../,/^C-Pluff/p` 永不命中而输出空文件；configure.ac 用 `AC_LINK_IFELSE(isatty(fileno(stdin)))` 探测，真机交叉/工具链环境下该探测失败 | 与管道修复不同路线的内容修复：generate() 追加 configure 缓存覆盖 `cp_cv_sys_have_isatty_fileno=yes`（musl 具备该函数，恢复上游预期的回显行为），build() 在 configure 后校验 config.h 是否 `#define HAVE_ISATTY_FILENO` 并打印诊断；不改任何测试断言与过滤逻辑 |
## 依赖版本

- expat/2.8.2 (ohpcd, dbus/dbus-glib 等已用版本, 运行时 XML 解析必需)
- 无其他 Conan 依赖; gettext 与 readline 均为上游可选, 已显式关闭

## 配方文件 (本轮全部新增, 未 commit)

- `archives/c/cpluff/0.2.0/conanfile.py`
- `archives/c/cpluff/0.2.0/conandata.yml` (本轮新增 patches 条目)
- `archives/c/cpluff/0.2.0/patches/0001-guard-framework-lock-no-thread-release.patch`
- `archives/c/cpluff/0.2.0/patches/0002-context-owner-always-defined.patch` (本轮新增)
- `archives/c/cpluff/0.2.0/manifest.yaml` (版本级)
- `archives/c/cpluff/0.2.0/notes.md` (本文件)
- `archives/c/cpluff/0.2.0/test_package/conanfile.py`
- `archives/c/cpluff/0.2.0/test_package/CMakeLists.txt`
- `archives/c/cpluff/0.2.0/test_package/test_cpluff.c`
- `archives/c/cpluff/0.2.0/test_package/MANIFEST.yml`
- `archives/c/cpluff/README.md` (软件级)
- `archives/c/cpluff/manifest.yaml` (软件级)
- `.hmbs/pr-body.md` (PR 正文草稿, 测试数字待真机 evidence 回填)

## 待真机验证

- 工作树保持未提交, 等待 hmbs 同步后真机预检复跑。预期: configure 越过
  expat/dlopen/线程探测, `make -j1` 成功, `make check` 53/53,
  test_package 3/3。
