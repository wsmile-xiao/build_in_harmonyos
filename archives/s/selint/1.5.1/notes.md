# selint 1.5.1 适配笔记

## 编译环境
- 构建系统: autotools（release tarball 自带预生成 configure / lex.c / parse.c，无需 autoreconf）
- 编译日期: 2026-10-09
- 编译器: clang (OHOS aarch64)
- 状态: success（设备实测，CI 同源脚本 build_and_test.sh 全绿，RC=0）

## 编译步骤
1. `init-build selint 1.5.1` 下载官方 release tarball 并解包。
2. 配方 `generate()` 产出：AutotoolsDeps（confuse -lconfuse、uthash -I、musl-fts -lfts）、
   PkgConfigDeps（check.pc 供 tests/ 的 PKG_CHECK_MODULES）、AutotoolsToolchain；
   另存 conanbuild_runpath：LD_LIBRARY_PATH（依赖共享库，供 configure conftest 与
   make check 测试程序解析）+ TEMP/TMPDIR（可写构建临时目录）。
3. `build()` 在 OHOS 上以 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh` 内联前缀运行 configure
   （避开 profile buildenv 指向 hnp bash 的 getcwd 问题）。
4. `make -j1`（E074：并行 make 触发 HMDFS jobserver fifo EPERM）。
5. `make check` 运行上游 Check 测试套件 —— **18 个 check_* 程序全部通过**。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 建临时目录报 Permission denied（subs1.awk） | E011/E052：config.status 模板 `umask 077 && mktemp/mkdir`，HMDFS setgid 下 drwx--S--- 目录属主不可写 | 配方 `_patch_configure_umask()` 去掉 umask 包裹，保留真实 mktemp/mkdir（confuse/3.4 同款先例） |
| 2 | configure 可能取到 hnp bash 作 SHELL 致 getcwd 失败 | E543：profile buildenv 把 SHELL/CONFIG_SHELL 指向 hnp bash，其在 HMDFS 构建目录下 getcwd 必挂 | 以 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh` 内联 env 前缀显式路由 |
| 3 | 并行 make 偶发 jobserver fifo EPERM | E074：HMDFS 对 GNU make 并行 jobserver 的 FIFO 权限限制 | `make -j1` |
| 4 | configure `cannot run C compiled programs`（conftest 报 `Error loading shared library libcheck.so`） | OHOS loader 无默认搜索路径，conan 缓存里的共享依赖（check/confuse/fts）不在其中；conanbuild 默认不含这些 lib 目录 | `generate()` 把所有依赖 libdir 前置到 LD_LIBRARY_PATH，存成 conanbuild_runpath 脚本；configure 调用传 `env="conanbuild"` |
| 5 | 编译报 `'fts.h' file not found` | E 系（musl 缺口）：musl 故意不提供 fts.h/libfts，而 selint 的递归目录扫描用 fts_open/fts_read/fts_set/fts_close | 增依赖 `musl-fts/1.2.7`（nnn/libselinux/afsctool 先例），补头+库 |
| 6 | 上游 18 个 Check 测试全部 FAIL，`check_msg.c:317 Unable to create temporary file` | check 的 `open_tmp_file()` 优先读 `TEMP`，其次 `P_tmpdir`（musl 上展开为 `/tmp`），最后才 `TMPDIR`；OHOS `/tmp` 只读，且 TMPDIR 在 musl 上永远到不了 | 环境变量设 **`TEMP`**（不是 TMPDIR）指向构建目录下可写 tmp，并存进 conanbuild_runpath |
| 7 | 安装后的 `selint` 二进制带 `DT_NEEDED libcheck.so`，test_package 报 `Error loading shared library libcheck.so`；且 test_package 首版断言期望 S-003 实得 C-005 | (a) check 原以 `requires(visible=False)` 声明，AutotoolsDeps 读 dependencies.host 把 -lcheck 拼进全局 LIBS，污染主二进制链接；(b) 测试样例 `{ read execute }` 未按字典序，触发的是 C-005（规则未排序）而非 S-003（调用未声明宏） | (a) check 改为 `test_requires`（teseq/1.1.1 先例）——check 只进 build/test 语境，主二进制不再链它，tests/ 仍通过 @CHECK_LIBS@ 拿到；(b) 断言改为实际稳定的 C-005，并用 `-F`（fail_on_finding）验证非零退出码 |

## 源码修改
- 无源码补丁（patches=0）。仅在 build() 期动态改写 configure 脚本的 umask 包裹（问题 #1）。

## 依赖版本
- confuse/3.4（libconfuse，链接进 selint 二进制；配方默认 shared=False → **静态**，故成品无 DT_NEEDED libconfuse）
- uthash/2.3.0（header-only，AC_CHECK_HEADER uthash.h）
- musl-fts/1.2.7（musl/OHOS 无 fts.h/libfts；selint 配方 `default_options={"musl-fts/*:shared": False}` **静态**链接，成品自包含）
- check/0.15.2（**test_requires**，仅 tests/ 套件通过 @CHECK_LIBS@ 链接；selint 主二进制不链接）
- flex/2.6.4 + bison/3.8.2（tool_requires，防御性声明；tarball 已预生成 lex.c/parse.c，实际不触发再生成）

## 验证结果（设备实测，2026-10-09）
CI 同源脚本 `ci/conan/build_and_test.sh`（CI_PACKAGES=archives/s/selint/1.5.1）：

| 门禁 | 结果 |
|---|---|
| L0 语法/静态 | pass |
| L1 上游测试 + test_package | pass（**18/18 上游 Check 测试通过**，test_package 功能测试通过） |
| L2 冒烟 --version | pass（裸跑即可，成品 DT_NEEDED 仅 libc.so） |
| L4 补丁 | pass |
| L5 bin/ 有内容 | pass |
| L1e 破坏性负例 (R34) | pass（移走 bin/ 后测试确实失败） |
| 合计 | BUILD_AND_TEST_RC=0，Pass rate 100% (1/1) |

上游测试声明：`make check` 实跑 18 个 Check 单元测试程序（**130 用例 / 130 通过 / 0 失败**，
逐程序 `Checks: N` 日志求和，与源码 130 处 `tcase_add_test` 静态计数一致）。

### 上游功能测试（bats，按上游 CI 同口径补跑）

上游 CI `main.yml` 的 "functional tests" 步骤是 `cd tests/functional && BATS_TIME_EXPENSIVE=1
bats end-to-end.bats`（`make check` 不含此套件，`FUNCTIONAL_TEST_FILES` 仅在 `EXTRA_DIST`）。
设备无 bats → 经 gh-proxy 拉取纯 bash 的 bats-core 1.11.1，按同一命令实跑：

- **56 用例：50 通过 / 2 跳过 / 4 失败**（bats 把 skip 也计入 ok：日志 OK_COUNT=52 含 2 个 skip）
- 失败逐类归因（平台差异，非移植缺陷；selint 核心解析/检查/报告功能全部正常）：
  1. `usage`：功能等价（退出码 64 + Usage 正常），仅 libc 报错文案差异——glibc
     `invalid option -- 'Z'` vs OHOS musl `unrecognized option: Z`（设备实测），测试 grep 的是 glibc 字面量
  2. `parse_error_printing` / `report format`：报告内容逐字正确，仅多一行
     `Warning: Failed to load classes and perms from current kernel.`——OHOS 暴露
     `/sys/fs/selinux/class`（F_OK 通过）但 LSM 拒绝读取（设备实测 Permission denied），
     `load_access_vectors_kernel` 走到 `SELINT_PARSE_ERROR` 分支打 Warning；上游测试只处理
     "SELinux 不存在"（Note，被 `grep -v '^Note: '` 过滤）与"可读"两种状态
  3. `parse_error_printing_valgrind`（失败）+ `valgrind`、`Broken config`（跳过）：
     设备无 valgrind（command not found, exit 127 实测）；上游 CI 经 apt 安装 valgrind

上游用例总数：**186**（130 单元 + 56 功能 bats），声明见 test_package/MANIFEST.yml。
