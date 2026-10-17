# riemann-c-client 1.10.4 适配笔记

## 编译环境
- 构建系统: autotools（上游 git archive 无 configure/，现场 bootstrap）
- 编译日期: 2026-09-25
- 编译器: clang/clang++ 15（-stdlib=libc++，profile ci/conan/profiles/ohos-aarch64）
- 状态: built

## 编译步骤（conan create 全链路，rc=0）

1. `get()` 下载源码：2026-09-25 换源——原官方 forge tag 归档（sha256 6b1e3aa6…，本机两次下载同值、与 tag 树 diff 逐字节一致）在 CI worker 侧连续 2 轮返回非确定性坏字节（build 60504/60512，Provided 恒定、Computed 两轮不同），属下载面问题；改用同一发行物的 Debian/Ubuntu 官方归档 `riemann-c-client_1.10.4.orig.tar.xz`（sha256 14b46c07…，Debian 官方 .dsc 公布值 + 三通道同值实测），解包树与 tag 树 `diff -r` 57 文件逐字节一致（三方取证详见 conandata.yml 头部注释）。
2. `apply_conandata_patches` 应用 5 个补丁（详见「源码修改」）。
3. 修正依赖 `.la` 的 `//lib` 残留路径（见问题 5）。
4. bootstrap：`libtoolize --force --copy` → `aclocal --force -I m4` → `autoheader --force` → `autoconf --force` → `automake --add-missing --copy`（PERL/PERL5LIB 钉到设备原生 perl，见问题 6）。
5. `configure --enable-shared --enable-static`（AutotoolsToolchain + AutotoolsDeps + PkgConfigDeps；pkg-config 探测 libprotobuf-c/check/json-c/gnutls 全部命中）。
6. `make -j1`（ACLOCAL/AUTOMAKE/AUTOCONF/AUTOHEADER=true 防维护者重跑）。
7. `make check`：automake serial-tests 跑 3 个 Check 程序，`CK_FORK=no`（上游 AM_TESTS_ENVIRONMENT 内置）。
8. `make install` → 按 `shared` 选项保留单态库 + 裁剪 .la → 安装树 11/11 实物清点 → 拷贝 LICENSE/LICENSE.GPL。
9. test_package：CMake 消费方构建 + ctest（1/1）+ 目标机 CLI 冒烟（`--help`/`--version` 退出码 0）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `You need protoc-c installed` | OHOS 构建主机与 CI 均无 protoc/protoc-c（同族 ocserv 1.5.0） | 本机 bootstrap：protobuf/3.17.3 的 protoc + protobuf-c 1.5.1 源码构建 protoc-gen-c，一次性生成 `riemann.pb-c.[ch]`（725+245 行）随补丁 0003 分发；configure.ac 降级为 WARN（0001）、Makefile.am 生成规则改 cp（0002） |
| 2 | bootstrap protoc-gen-c 时 `target not found: zlib::zlib` | ohpcd protobuf/3.17.3 的 protobuf-targets.cmake 引用 `zlib::zlib` 但 protobuf-config.cmake 无 find_dependency（包级缺陷） | `-DCMAKE_PROJECT_INCLUDE=zlibshim.cmake` 注入 `zlib::zlib` IMPORTED target（指向 conan zlib 的 libz.a），构建通过 |
| 3 | configure `cannot run C compiled programs`（rc=127） | conftest 链到 .so 后加载器找不到：ohpcd gnutls/libgcrypt **conaninfo 标 shared=False 但实物只打包 .so** | `_environment()` 给 configure/make/check 注入全部依赖 lib 目录的 LD_LIBRARY_PATH（构建期只影响运行探测，链接器仍用 -L） |
| 4 | configure `cannot guess build type`（uname -s=HarmonyOS） | bootstrap 落盘的 config.guess（automake 1.18 自带，2024-07-27）不识 HarmonyOS | 补丁 0004：HarmonyOS 分支注入 → 输出 `aarch64-unknown-linux-ohos`（新件整文件补丁；`--add-missing` 不覆盖既有文件）。实测 config.sub 2024-05-27 已原生接受 linux-ohos，无需补 |
| 5 | 链接 `//lib/libgpg-error.la is not a valid libtool archive` | ohpcd 二进制包 `.la` 带 `prefix=/` DESTDIR 残留（E236 族） | 配方内消费者侧修正器（cattle-1.0/arm-none-eabi-gdb 先例）：改写 libdir/dependency_libs 为实际缓存路径，实修 libtasn1/libgcrypt/libgpg-error/gmp 四个 .la，日志行可 grep |
| 6 | automake 脚本 `Perl_my_cxt_init` 崩溃风险 | conan Perl 与设备原生 Perl ABI 不一致（device-facts §一.23） | ding-libs 先例：每条 bootstrap 命令前缀 `PERL=/data/service/hnp/bin/perl PERL5LIB=<automake share>` |
| 7 | `json.h` file not found | 源码裸 include `<json.h>`（发行版靠 json-c.pc 的 `-I…/json-c`），conan 重生成的 json-c.pc 只带 include 根 | AutotoolsToolchain extra_cflags 注入 `…/include/json-c` |
| 8 | make check `duplicate symbol: riemann_message_to_buffer` | 上游测试用测试对象**覆盖**库符号（mock 拦截），只在链接共享对象时成立（上游 CI 即如此）；纯静态链接必撞 | 双态构建（--enable-shared --enable-static）让测试按上游原生形态链接 .so；打包按选项留单态；补丁 0005 给 CLI 加 per-target `-static`，保证 CLI 与单态包自洽 |
| 9 | test_package 运行期 `gnutls_*: symbol not found` | VirtualRunEnv 按**声明选项**（shared=False）生成 LD_LIBRARY_PATH，漏掉实物为 .so 的 gnutls；另 conan `self.run(env="a,b")` 字符串按**单文件名**解析（不切逗号） | test_package 扫描所有含 .so 的依赖 lib 目录生成 extrasharedlibs 脚本，`env=["conanrun","extrasharedlibs"]` 列表形式传入 |

## 源码修改（5 个补丁，全部 portability）

| 补丁 | 内容 |
|------|------|
| 0001-configure.ac-protoc-c-optional.patch | protoc-c 缺失由 AC_MSG_ERROR 降级为 AC_MSG_WARN（改用随包预生成文件） |
| 0002-Makefile.am-use-pre-generated-pb-c.patch | pb-c 生成规则 `protoc-c … --c_out` 改为 `cp -f` 预生成文件到构建树 |
| 0003-pre-generated-protobuf-c-sources.patch | 新增 lib/riemann/proto/riemann.pb-c.c/.h（protoc 3.17.3 + protoc-gen-c/protobuf-c 1.5.1 生成；/dev/null 源、strip=0） |
| 0004-build-config.guess-ohos.patch | 新增 config.guess（automake 1.18 基线 + HarmonyOS 分支 → aarch64-unknown-linux-ohos） |
| 0005-Makefile.am-static-cli-link.patch | CLI 增加 per-target `-static`（单态包内 CLI 不依赖被裁掉的 .so） |

补丁三关门禁（止损先例 18）：NUL=0 ∧ hunk≥1 ∧ patch_ng/CLI patch 真 apply 后与目标树逐字节 cmp 一致——0001–0005 全过。

## 依赖版本

- 运行/链接：protobuf-c/1.5.1（公共头穿透，transitive_headers=True）、gnutls/3.8.10（TLS 特性 + 2 个 TLS 用例注册）、json-c/0.18（CLI JSON 输出）
- 工具：autoconf/2.72、automake/1.18、libtool/2.5.4、pkgconf/3.0.6（pkg.m4）
- 测试：check/0.15.2（test_requires）
- 全部依赖 W0 阶段 `conan list -r=ohpcd` 实查 + ohos armv8 预编译二进制核对通过

## 验证结果

```bash
# 开发轮全链路（conan create rc=0）
conan create archives/r/riemann-c-client/1.10.4 -pr:h=$HOST_PROFILE -pr:b=$HOST_PROFILE --build=missing
# 上游测试（make check，serial-tests，CK_FORK=no）
#   PASS: tests/check_libriemann   100%: Checks: 37, Failures: 0, Errors: 0
#   PASS: tests/check_symver       100%: Checks: 2, Failures: 0, Errors: 0
#   PASS: tests/check_networked    100%: Checks: 0, Failures: 0, Errors: 0
# 安装树：install_tree_check: 11/11 expected files present
# test_package: ctest 1/1 Passed；riemann-client --help/--version 目标机退出码 0
```

- 上游用例清点：START_TEST==END_TEST==tcase_add_test 三口径逐文件一致 **N=54**（含 check_networked 15 项网络用例）；`ck_assert*` 断言 374。
- 本机实跑 **N′=39 全过**；差额 15 = check_networked 全部用例，**注册只由 `RCC_NETWORK_TESTS` 环境变量门控**（设备不设该变量 → 上游默认不注册、跑空套件），计 NOT_RUN；真实 Riemann 服务是上游 CI 中这些用例的**通过条件**而非注册条件。上游该程序自带「空套件即通过」的设计，非适配失败。

## 注意事项

- `make check` 需要构建树内可写 TMPDIR（/tmp 只读），配方 `_environment()` 已钉 TMPDIR/TMP/TEMP=build/tmp。
- conaninfo 与实物不符的 registry 包（gnutls/libgcrypt 标 shared=False 实为 .so）是本包 LD_LIBRARY_PATH 注入与 test_package 扫描器的直接原因，已在配方内注释留痕。
