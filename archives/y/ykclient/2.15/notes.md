# ykclient 2.15 适配笔记

## 编译环境
- 构建系统: autotools（GitHub tag 归档无预生成 configure，配方内 `autoreconf -fi` 自举）
- 编译日期: 2026-09-21
- 编译器: clang / clang++（OHOS aarch64，profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built（conan-verify + finish 通过，尚未 release/upload）
- 依赖: `curl/8.15.0.1`（require）；`automake/1.18`、`libtool/2.5.4`（tool_requires）
- 交付形态: 静态库 `libykclient.a` + 命令行工具 `bin/ykclient`（实测包目录内确有
  `bin/ykclient`）。按 R38/CI L0k 的『产物含可执行文件即须声明』口径，配方显式给出
  `cpp_info.bindirs = ["bin"]`，并补软件级 `archives/y/ykclient/commands.json`；
  `package_type` 仍为 library（主交付物是库，工具只是随附）。

## 编译步骤

```bash
autoreconf -fi                                        # 归档无 configure
./configure --build=aarch64-unknown-linux-gnu \
            --host=aarch64-unknown-linux-ohos \
            --enable-static --disable-shared \
            PKG_CONFIG_PATH=<conan generators>        # PkgConfigDeps 出 .pc 供 PKG_CHECK_MODULES(libcurl)
make -j1 HELP2MAN=/bin/true dist_man_MANS=            # E289：OHOS 无 help2man
make -j1 check HELP2MAN=/bin/true dist_man_MANS= \
     INCLUDES=-I<build_folder>                        # VPATH 生成头可见性，见问题 4
# check 前注入 LD_LIBRARY_PATH（见问题 5）；编译期以 -DTEST_WITHOUT_INTERNET 启用上游离线开关
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `AttributeError: 'AutotoolsToolchain' object has no attribute 'cpp_flags'`（generate() 期即挂，G2 秒失败） | conan 2.29 的 AutotoolsToolchain 只提供 `extra_cflags/extra_cxxflags/extra_ldflags` 三个追加槽，无 `cpp_flags/ld_flags` | 改为 `tc.extra_cflags.append(...)`；同批把依赖 include/lib 由 `cpp_info` 相对路径改为 `package_folder` 绝对拼接 |
| 2 | `configure: error: working directory cannot be determined`（E386 家族） | ohos-aarch64 profile 的 `[buildenv]` 把 `SHELL/CONFIG_SHELL` 钉在 `/data/service/hnp/bin/bash`，该 bash 在 HMDFS 构建目录内 getcwd 必挂；`conanbuildenv-*.sh` 每次应用都会覆盖 `os.environ`，故 `env -u CONFIG_SHELL` 包命令法无效 | 照已合入的 `psocksxx/1.1.1` 先例：`build()` 首次 `self.run()` 之前，把 `generators_folder` 下全部 `*.sh` 里的 hnp bash 文本替换为 `/bin/sh` 并同步 `os.environ`（**不**用同名 `save_script("conanbuild")`，那会自递归空转） |
| 3 | `make: *** [Makefile:1219: ykclient.1] Error 127`（`build-aux/missing[85]: help2man: inaccessible or not found`） | 上游 `dist_man_MANS = ykclient.1` 由 help2man 现场生成，OHOS 无 help2man（仅有 perl/pod2man） | 按 E289：`make`/`make check`/`install` 一并传 `HELP2MAN=/bin/true` **且** `dist_man_MANS=`。E289 明确记录只设 `HELP2MAN` 会在 install 阶段因产物不存在再次失败 |
| 4 | `tests/../ykclient.h:40:10: fatal error: 'ykclient_version.h' file not found`（`make check` 编 selftest 时） | 影子构建（`srcdir != builddir`）下 automake 给 `tests/` 生成的 `DEFAULT_INCLUDES = -I. -I$(srcdir)`（实测 `build-release/tests/Makefile:158`），**不含 `-I$(top_builddir)`**，而 `AC_CONFIG_HEADERS` 产物 `ykclient_version.h` 只落在 build 目录；native 构建 `srcdir==builddir` 故上游不显现 | `make check` 命令行追加 `INCLUDES=-I<build_folder>`：`INCLUDES` 在生成的两个 Makefile 里都未被赋值，是 COMPILE 里的纯追加槽；**不能**用 `AM_CPPFLAGS`——根 `Makefile.am:31` 用它承载 `$(LIBCURL_CFLAGS)`，命令行覆盖会丢 curl 头路径 |
| 5 | `FAIL selftest (exit status: 127)` + `Error loading shared library libcurl.so: (needed by ./selftest)` | musl 动态加载器忽略 `DT_RUNPATH`，测试二进制运行期只认 `LD_LIBRARY_PATH`（conan 依赖库不在系统搜索路径） | `make check` 前把 curl 包 libdir（绝对）、`<build_folder>`、`<build_folder>/.libs` 与 `<build_folder>/tests/.libs` 注入 `LD_LIBRARY_PATH`（先例 `acedb/4.9.62`、`4ti2/1.6.10`）。`llvm-readelf -d libcurl.so` 实测其 `NEEDED` 仅 `libc.so`（openssl/zlib 已静态链入 curl 包），故无需再传递归依赖目录 |
| 6 | 消费者测试首跑 3 条断言失败（`FAIL 43/45/60`） | 断言期望写反：`ykclient_check_version(req)` 实测语义是「`req` 为 NULL 或 `req<=库版本` → 返回库版本串，仅 `req` 更高 → NULL」（`ykclient_version.c:124-131`，与上游 `tests/selftest.c:210-228` 一致）；`ykclient_set_client_b64()` 走上游 rfc2045 解码器，非法字符被宽松跳过，无 `BASE64_DECODE_ERROR` 返回路径（`ykclient.c:532-563`） | 按源码与上游 selftest 的实际契约改正三条断言（**只改我们新增的消费者测试，不动上游用例**），改后 `consumer_test: PASS (0 failures)` |

另：`configure` 里的 `umask 077 && mktemp -d` 包裹按 E114 在 `build()` 内就地改写（HMDFS setgid 使临时目录不可写）；`configure` 是 tarball 内生成文件，按 R6 不产 `patches/`，改写与未命中告警都在配方里。

## 源码修改

无上游源码补丁（`patches_applied: []`）。全部适配动作发生在配方内：生成文件（configure / conan 聚合 env 脚本）就地改写 + make 命令行变量覆写，均可审计、不污染上游源码。

## 依赖版本

- `curl/8.15.0.1`（制品仓已发布，`conan download --only-recipe` 实测）
- `automake/1.18`、`libtool/2.5.4`（tool_requires，制品仓已发布）

## 测试账本（五维口径，AGENTS §10.1）

| 维度 | 数值 | 口径与来源 |
|---|---|---|
| `N_static` 上游静态声明 | **27** | `tests/selftest.c` 的 `TEST(` 标记点共 36 处，其中 9 处位于上游 `#if 0` 死区（awk 实测），活跃 27 |
| `N_registered` 构建系统注册 | **1** | `tests/Makefile.am:37 TESTS = $(check_PROGRAMS)`，注册的是单个 runner `selftest` |
| `N_executed` 实际执行 | **runner 1/1；内部 21 个 TEST() 点进入，其中 6 点完整离线断言、15 点内的网络断言走 SKIPPED 分支（共 16 次 `Test SKIPPED` 标记）** | `make check` 实跑，`tests/test-suite.log`：`# TOTAL: 1 / PASS: 1 / FAIL: 0 / ERROR: 0`；逐点分类见 `tests/selftest.log`（21 个 `Test ...` 头行，awk 按头行分段统计） |
| 未执行/排除 | **6 点**（静态 27 − 进入 21） | 这 6 个 `TEST()` 点位于上游 `#ifndef TEST_WITHOUT_INTERNET` 区块内，启用离线开关后由**上游自身**从编译中排除，非本次删改 |
| `N_consumer` 新增消费者测试 | **1 个程序 / 15 条断言** | `test_package/consumer_test.c` 真实编译 + 链接 `libykclient`/`libcurl` + 运行，`LastTest.log`：PASS 15 / FAIL 0，末行 `consumer_test: PASS (0 failures)` |

### 15 个进入点里的 16 次网络断言跳过：逐项原因

上游 selftest 的网络断言形如「设好 client key → 向 Yubico 在线校验端点
`api.yubico.com/wsapi/2.0/verify`（wsapi v1）发真实 HTTP 请求 → 断言返回
`REPLAYED_OTP`/`BAD_SIGNATURE`」。该端点/协议已由服务方停用（现返回 HTTP 403），
断言目标在任何环境都已不成立，与本库适配无关。上游作者为此自带离线开关
`TEST_WITHOUT_INTERNET`：网络断言块被 `#ifndef TEST_WITHOUT_INTERNET` 包住，
未定义时执行请求、定义后打印 `Test SKIPPED` 并继续。配方按上游设计意图在编译期
加 `-DTEST_WITHOUT_INTERNET`，于是：

- 15 个进入点（`selftest.c:240/253/265/287/302/317/351/366/383/395/407/426/445` 与
  `test_v1_validation` 的 `:56/:71`）各打印 1 次 `Test SKIPPED`（`:317` 因循环打印 2 次，合计 16 次）；
  这些点的**离线部分（句柄初始化、hex/b64 密钥设置、URL 模板设置）仍然真实执行并断言**，只有最后的网络比对被上游分支跳过；
- 另外 6 个点（`:235 init self`、`:277/282` 两个 `HEX_DECODE_ERROR`、`:466/470` 两个 `strerror`、
  `test_v1_validation:48 init self`）为纯离线用例，完整真实断言执行。

未删除、未屏蔽、未改判任何上游用例：runner 仍以真实退出码参与 `make check`
（此前 3 条断言写错时它就红过，见问题 6），`test-suite.log` 的 `FAIL: 0` 是执行结果而非设置。

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify ykclient 2.15     # G0/G1/G2/G3/G4 全 PASS，rc=0
#   tests/test-suite.log: TOTAL 1 / PASS 1 / FAIL 0
#   selftest.log        : 21 个 TEST() 进入点（15 点内的网络断言走上游 SKIPPED 分支，
#                            合计 16 行 Test SKIPPED；另 6 点为纯离线完整断言）
#   LastTest.log        : 15 断言 PASS / consumer_test: PASS (0 failures)
```

- 上游套件：注册口径 runner **1/1** 通过（`test-suite.log` TOTAL 1 / PASS 1 / FAIL 0）；原子口径 **21 个 TEST() 标记点全部进入执行、0 失败** —— 其中 6 点为纯离线完整断言，15 点内的网络断言走上游自带离线开关（合计 16 次 `Test SKIPPED`）。
- 新增消费者测试：1/1 程序通过（15 条断言全过）。

### 口径复算原始输出（本轮真机，逐条可重跑）

```
$ grep -cE '^[[:space:]]*TEST\('  tests/selftest.c          -> 36
$ awk '/#if 0/{f=1} /#endif/{f=0} f&&/TEST\(/{c++} END{print c+0}'       tests/selftest.c                                        -> 9   (36-9=27 活跃)
$ grep -c 'ifndef TEST_WITHOUT_INTERNET' tests/selftest.c     -> 16  (指令行数)
$ awk '/#ifndef TEST_WITHOUT_INTERNET/{d=1} /^#endif/{d=0} d&&/TEST\(/{c++} END{print c+0}' \
      tests/selftest.c                                        -> 6   (开关区内 TEST() 点数)
$ grep -c '^Test /'  tests/selftest.log                       -> 21  (运行进入)
$ grep -c 'Test SKIPPED' tests/selftest.log                   -> 16  (SKIPPED 次数)
  按头行分段：含 SKIPPED 的进入点 15、无 SKIPPED 的进入点 6
$ sed -n '4,12p' tests/test-suite.log
  # TOTAL: 1  # PASS: 1  # SKIP: 0  # XFAIL: 0  # FAIL: 0  # XPASS: 0  # ERROR: 0
$ grep -cE '^PASS ' <test_package>/.../Testing/Temporary/LastTest.log  -> 15
$ grep -cE '^FAIL ' 同上                                               -> 0
```

## 已知限制

1. 手册页 `ykclient.1` 不生成也不安装（OHOS 无 help2man，见问题 3）。库与命令行工具本体不受影响。
2. 在线校验路径（`ykclient_request` 的 HTTP 往返）在本平台无法端到端验证——依赖的外部服务已停用，非适配缺陷；离线 API（句柄/密钥/URL 模板/错误码/版本协商）全部有真实断言覆盖。
3. 交付为静态库形态（`shared=False` 默认）；`package_type = "library"`，消费者仍需自行链接 curl。
---

**编译结束**: 2026-09-22 02:12
**最终状态**: built
