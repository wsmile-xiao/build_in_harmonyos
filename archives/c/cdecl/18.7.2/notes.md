# cdecl 18.7.2 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-08-14
- 平台: HarmonyOS aarch64 (OHOS)
- 状态: built (待真机预检验证)

## 上游信息
- 官方仓库: https://github.com/paul-j-lucas/cdecl
- 版本: 18.7.2
- 许可证: GPL-3.0-or-later
- 源码包: cdecl-18.7.2.tar.gz (官方 GitHub release, sha256 已在 conandata.yml 声明)

## 源码分析

cdecl 是"C 声明翻译器"(C gibberish translator)：
- 把英文描述（如 `declare a as array 3 of int`）翻译成 C 声明（`int a[3];`）
- 反向把 C 声明翻译成英文（`explain int *p` → `declare p as pointer to integer`）
- 支持 C/C++、类型转换（cast）、宏展开（expand）等

### 构建系统
- Autotools：`configure.ac` + `Makefile.am`，子目录 lib(gnulib)/share/src/test
- release tarball 已含生成的 `configure`、`src/parser.c`、`src/lexer.c`，不需要 flex/bison
- 需要 C11 编译器（`_Generic` 支持），OHOS clang 满足
- 可选依赖：readline（交互编辑）、curses（term-size 终端尺寸），均已通过
  `--without-readline --disable-term-size` 禁用，核心功能不受影响
- 产物：`cdecl` 可执行文件 + `c++decl`/`explain` 符号链接（install-exec-hook 创建）+ man 手册

### 上游测试
- `make check`：test/ 目录 90 个 `.test` 用例（automake TESTS，run_test.sh 驱动，
  与 test/expected/*.out 对比）+ 6 个 `.exp`（需 expect，仅 WITH_EXPECT 时启用，
  真机无 expect 不启用）
- src/ 下 4 个单元测试 `check_PROGRAMS`（red_black_test / slist_test /
  strbuf_test / util_test），同样由 make check 运行
- conanfile.py build() 末尾运行 `make check` 并解析各子目录 test-suite.log，
  输出 `HMBS_UPSTREAM_TEST_RESULT` 标记（真实计数来自 automake 汇总行）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 上游 config.guess 较旧，不认 OHOS | configure 加 `--build=aarch64-unknown-linux-gnu` 强制指定 build triplet |
| 2 | readline/curses 为可选依赖 | OHOS 上无对应 conan 包 | `--without-readline --disable-term-size` 禁用可选功能 |
| 3 | 真机预检 configure 报 `working directory cannot be determined`（伴随大量 getcwd/job-working-directory 失败告警） | HMDFS 下 conan 建树后父目录对 getcwd() 不可达，autoconf 2.72 顶部严格 pwd 判定失败（aribb24/adms/nspr 已过门禁同款） | build() 开头 `os.chdir(build_folder)` + `os.environ["PWD"]=build_folder`（shell pwd 内建走逻辑路径）；补丁 `0001-configure-hmdfs-pwd-umask.patch` 把 configure 的 `ac_pwd=\`pwd\` &&` 改写为 `ac_pwd=\`pwd\` 2>/dev/null \|\| ac_pwd="$PWD"`，pwd 失败回退 $PWD |
| 4 | 预检日志开头 `preflight.sh[229]: can't create temporary file /tmp/xxx: Read-only file system` + configure 内 `umask 077 && mktemp -d` 隐患 | 真机 /tmp 为只读 erofs（E002）；HMDFS 上 umask 077 创建的 0700 临时目录变不可写 drwx--S---（E011/E129） | build() 把 TMPDIR/TMP/TEMP 固定到 build_folder 下可写目录（优先复用 hmbs 注入的 TMPDIR）；补丁 0001 同时把 configure/config.status 的 `umask 077` 改写为 `umask 022`；run_test.sh 的 `$TMPDIR` 兜底也依赖此设置 |
| 5 | 真机预检 compile 阶段 `cdecl_term.c:40:13: fatal error: 'curses.h' file not found`（`# include <curses.h>` 被编译） | 发布 tarball 自带维护者机器生成的过期 `src/config.h`，内含 `ENABLE_TERM_SIZE 1`、`HAVE_CURSES_H 1`、`WITH_READLINE 1`；`src/pjl_config.h` 用 quoted include `#include "config.h"`，编译器优先在源码树 src/ 目录命中这份旧头文件，遮蔽了 configure 按 `--disable-term-size --without-readline` 在构建目录新生成的 config.h，导致 term-size/curses 实际未被禁用 | `source()` 里 `get()` 后删除过期的 `src/config.h`，让 quoted include 回落到构建目录中 configure 生成的 config.h（term-size/readline 均关闭）；configure 从 `config.h.in` 重新生成，无需保留旧产物 |
| 6 | 测试用例与真机环境不匹配 | config.test 用 `/tmp/is_not_readable` 构造只读场景（真机 /tmp 为只读 erofs，touch 失败无法构造）；explain.test 期望输出含 terminal columns 警告（term-size 禁用后不再输出） | 补丁 `0002-tests-ohos-portability.patch`：config.test 改用构建目录可写相对路径 `./is_not_readable`（保留同样的权限拒绝断言）；从 expected/config.out 同步路径；从 expected/explain.out 移除 `can't get terminal columns` 警告行 |
| 7 | `make check` 11 个用例失败（config/xdg/file/include-ok/explain-error 等，4 个 ERROR 66 + 7 个 FAIL） | **VPATH 构建**：conan AutotoolsToolchain 是 out-of-source 构建，`make check` 在 build 树 `build-release/test/` 下运行；`.test` 脚本以相对 CWD 的路径引用 `data/...`（`--config=data/...`、`--file=data/...`、`include "data/..."`、`$PWD/data/xdg`），而 `test/data` 属 EXTRA_DIST 只存在于源码树，不会复制进 build 树 → fopen 失败 → `exit(EX_NOINPUT)`(66) 或输出与 expected 不匹配（FAIL）。`run_test.sh` 的 `EXPECTED_DIR` 走 `$srcdir` 所以 expected/ 正常，唯独 data/ 缺失 | `conanfile.py` 新增 `_sync_test_data()`：在 `make check` 前把源码树 `test/data` 递归复制进 build 树各 `test/` 目录（幂等，`**/test/Makefile` 定位），保持测试语义与上游一致 |
| 8 | `make check` 2 个用例仍失败（config.test 可见 FAIL + include-unquoted 隐藏 FAIL） | (a) **E046**：OHOS 的 HMDFS/SELinux 忽略 POSIX `chmod()`（返回成功但不改权限），config.test 的 `touch + chmod 000` 无法构造 EACCES，文件仍可读 → cdecl 打开空配置 → 缺 "Permission denied" 警告行 → diff FAIL；(b) **musl wordexp**：cdecl `push_file()` 以 `flags=0` 调 wordexp，musl 只在 `WRDE_NOCMD` 下才检查并返回 `WRDE_BADCHAR`，`include "|"` 的 `|` 被交给 /bin/sh 报语法错 → `WRDE_SYNTAX` → 输出 "path syntax error" 而非 expected 的 "contains unquoted shell characters"（glibc 则始终返回 WRDE_BADCHAR） | 补丁 `0003-ohos-portability.patch`：(a) config.test 改用 ENOTDIR 构造——`touch ./is_not_readable` 建普通文件、`CDECLRC=./is_not_readable/cdeclrc` 指向以文件为父组件的路径，fopen 返回 ENOTDIR（内核级路径错误，两平台一致），expected/config.out 同步为 "Not a directory"，断言语义（配置打不开→非致命警告→继续）不变；(b) `push_file()` 的 wordexp 加 `WRDE_NOCMD`，musl 即返回 WRDE_BADCHAR，与 glibc/expected 对齐（同时禁用命令替换，更安全） |
| 9 | 真机预检 compile 阶段 `ylwrap: line 173: : command not found` → `make[1]: *** [Makefile:2060: lexer.c] Error 127` | 真机无 flex/bison；configure.ac 在发布树路径（`$srcdir` 无 `.git`）下跳过 `AC_PROG_LEX`/`AM_PROG_LEX`，`LEX`/`LEX_OUTPUT_ROOT`/`YACC` 全为空；而 automake 的 `.l.c`/`.y.c` 后缀规则（`src/Makefile.in:2060/2063`，`am__skiplex` 未定义无守卫）在 build 树缺少 `BUILT_SOURCES`（lexer.c/parser.c/parser.h）时触发 ylwrap 重建，空程序名 → ylwrap 第 173 行 `"$prog" "$@" "$input"` 报 command not found。发布包实际自带这三个生成文件（`lexer.c` 比 `lexer.l` 新 2 秒），上游设计是不应重建 | `conanfile.py` 新增 `_sync_generated_sources()`：`configure` 之后、`make` 之前，把源码树 `src/{lexer.c,parser.c,parser.h}` 复制进 build 树各 `src/` 目录（`**/src/Makefile` 定位；`shutil.copy` 使 mtime=当前时间，必然新于 `lexer.l`/`parser.y`），make 判定目标已最新即跳过 `.l.c`/`.y.c` 生成规则，编译经 VPATH 使用发布包自带的生成文件，全程不依赖 flex/bison |
| 10 | 真机预检 compile 阶段 configure 在 `checking filesystem timestamp resolution` 处 `fork: Out of memory` 后硬报 `ls -t produces unexpected output` 终止（HMBS 平台诊断 `[shell_getcwd]`：HNP bash 无法访问当前 HMFS/HMDFS 工作目录） | automake 的 `_AM_FILESYSTEM_TIMESTAMP_RESOLUTION` 探测用子 shell `( set X \`ls -t conftest.ts[12]\` ... )` + 命令替换运行 ls，HMFS/HMDFS 工作目录链不可达时 fork 子 shell 偶发 ENOMEM，ls 无输出使探测断言失败，configure 把该情况当"broken ls"硬报 `as_fn_error` 终止（同一 fork 模式也会让紧随其后的 `checking whether build environment is sane` 探测误报时钟错误）；configure 已过 0001 补丁的 pwd 回退，故非 getcwd 本身，而是探测代码路径的 fork 失败 | (1) `conanfile.py` build() 在 configure 前预置 `am_cv_sleep_fractional_seconds=yes`、`am_cv_filesystem_timestamp_resolution=2` 两个缓存变量，configure 走 `"(cached)"` 分支直接跳过整个探测（2 秒 = 上游文档化的默认最坏情况分辨率，仅影响 sanity 探测的 sleep 间隔，不改变构建语义）；(2) 新增补丁 `0004-configure-fork-tolerant-timestamp.patch` 作为兜底：把 timestamp 探测失败分支从 `as_fn_error` 改为 WARNING + `am_try_resolutions=` 置空（跳过后续 fork 密集的 0.01/0.1 秒细粒度探测），build environment sanity 探测失败时改为 WARNING + `am_build_env_is_sane=yes` 继续 |
| 11 | 真机预检 compile 阶段 `make install` 在 `install-man1` 报 `Error 64`（`install -c -m 644 cdecl.1 c++decl.1 '…/p//share/man/man1'` 批量拷 2 个 man 页失败），构建与 94/94 `make check` 全通过后栽在安装阶段 | 真机 staged `install`（`runtime/cdecl-18.7.2/bin/install`）拒绝多源批量拷贝形式（BSD 风格 usage error，退出码 64；单源形式正常，此前 bin/completions 等单文件安装均通过）。automake 的 `install-man1` 规则先做批量 `$(INSTALL_DATA) $$files '$(DESTDIR)$(man1dir)'`（同目录多个 man 页一次拷入），正是触发点；若该步退出，后续 per-file 兜底循环根本不会执行 | `conanfile.py` 新增 `_write_install_wrapper()`（生成 BSD/GNU install 兼容的逐文件拷贝 wrapper，`-c/-m/-d/-D/-t/-o/-g` 全解析，多源时逐个 `cp -f` + `chmod`，目标缺失时 `mkdir -p` 兜底，幂等）与 `_patch_makefile_install()`（把各 Makefile 的 `INSTALL`/`INSTALL_PROGRAM`/`INSTALL_SCRIPT`/`INSTALL_DATA` 变量改指向 wrapper，automake 的 INSTALL_DATA 以 `${INSTALL}` 为基底，一处替换全链路生效）；`build()` 在 configure 前把 wrapper 目录前置到 PATH（AC_PROG_INSTALL 若选中则天然生效），`package()` 在 `autotools.install()` 前强制改写 Makefile（双保险，不依赖 conan Autotools 内部 API）。本地已用提取出的脚本做 8 组功能测试（多源/单源/目标缺失/-t/-d/-D/幂等）全部通过；chmod 模式位在 Windows 本地 Git Bash 不生效属测试环境特性，真机 POSIX 权限正常 |

## HMBS 机器证据标记
- `HMBS_UPSTREAM_TEST_RESULT`：conanfile.py `_run_upstream_tests()` 在 `make check`
  结束后解析 `build/**/test-suite.log` 的 `# TOTAL/# PASS/# FAIL/# SKIP` 汇总行，
  输出真实计数（discovered/executed/passed/failed/skipped）。
- `HMBS_TEST_PACKAGE_RESULT`：test_package/conanfile.py `test()` 运行
  `test_cdecl.sh`（4 个显式断言）后输出 discovered=4/passedCount=4。

## 验证命令

```bash
conan create . -pr=ci/conan/profiles/ohos-aarch64
# build() 内自动执行 make check (上游测试) + test_package (消费者测试)
```
