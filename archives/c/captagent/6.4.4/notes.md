# captagent 6.4.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-30
- 编译器: clang/clang++（OHOS aarch64 profile ohos-aarch64）
- 状态: built

## 编译步骤
1. `conan create archives/c/captagent/6.4.4 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
2. tarball 无 configure → build() 首步 `_fix_captagentconf_data()`（autoreconf 前）→ `autoreconf -fi`（tool_requires automake+libtool+pkgconf）
3. `_drop_umask_077()`（configure 内嵌 umask 077，HMDFS 临时目录不可写 E011/E114）
4. AutotoolsToolchain：`--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`（E007，build 必须 gnu）
5. AutotoolsDeps + PkgConfigDeps（依赖 include/lib 自动注入）
6. `make check` 执行留证据（上游无集成测试，各目录 Nothing to be done）
7. package(): autotools.install() + 删 `*.la`/`*.a`（libtool 辅助文件）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.status: can't create ./confXXX/subs1.awk: Permission denied` | configure 生成的 config.status 用 `umask 077 && mktemp -d`，HMDFS 上 0700+setgid 目录不可写（E011/E114） | `_drop_umask_077()`：对 configure 文本替换两处 umask 077（改 configure 即生效，config.status 生成时带干净模板） |
| 2 | `cannot guess build type`（E007） | config.guess 不识别 HarmonyOS | `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`（都写 ohos → configure 误判非交叉 → "cannot run C compiled programs"） |
| 3 | `make: No rule to make target '.../conf/captagent.xml'`（out-of-source 构建） | 上游 src/Makefile.am 的 `captagentconf_DATA = $(top_srcdir)/conf/captagent.xml` 指向**源目录**，但该文件是 configure 生成物（config.status 从 .in 生成，只在 build 目录）——源 tar 里没有 | `_fix_captagentconf_data()`：build() 内联把 DATA 改 `$(top_builddir)/conf/$(sbin_PROGRAMS).xml`（autoreconf 前执行让 automake 重生成 Makefile.in；ekg2 E322 同类 out-of-source 缺陷） |
| 4 | `configure: error: bison not found / flex missing yypop_buffer_state` | configure.ac 硬性 AC_PROG_LEX(>=2.5.33)/AC_PROG_YACC 检查，CI 无系统级 flex/bison | tool_requires `flex/2.6.4` + `bison/3.8.2`（制品仓已发布） |
| 5 | libuv 硬依赖 | configure.ac 320-324 行**无开关守卫**（useLIBUV=yes 默认），无条件 AC_CHECK_HEADER(uv.h)+AC_CHECK_LIB(uv) | 制品仓有 libuv/1.52.1，直接 requires；适配前逐行读 configure.ac 查守卫（勿只信 README） |
| 6 | 官方任务平台标 C++ / 1.0.0 | 平台自动导入误判（captagent 实测 43 .c / 0 .cpp，纯 C；真实版本 6.4.4） | 语言/版本字段不可信，以源码实测为准；自建正确版本任务（§六b） |

## 源码修改（0 patch，build() 内联处理）
- `_fix_captagentconf_data()`：src/Makefile.am 的 captagentconf_DATA 指向 $(top_srcdir)/conf/ → $(top_builddir)/conf/（out-of-source 缺陷）
- `_drop_umask_077()`：configure 删 umask 077（E011/E114）
- 未用 patch：refresh-patch 会重排编号且覆盖 build() 内联改动（ekg2 经验），两处修复放 build() 内联稳定可复现

## 依赖版本
- 在仓：expat/2.8.2.1.1、libpcap/1.10.6、json-c/0.18、libuv/1.52.1（全部硬依赖，制品仓已发布）
- tool：automake/1.18、libtool/2.5.4、pkgconf/3.0.5（autoreconf）、flex/2.6.4、bison/3.8.2（configure 硬检查）
- pthread/dl：musl libc 自带
- 可选功能默认关闭（--enable-compression/ssl/epan/pcre/redis/tls/extramodules 均未启用，不引入 zlib/openssl/wireshark/pcre/hiredis/gcrypt 依赖）

## 验证结果
```bash
# conan-verify 8 门禁全过（G0-G4 + L2/L4/L5）
# test_package 2/2 断言：
#   captagent_test: OK  'captagent -v' -> contains '6.4.4'
#   captagent_test: OK  'captagent -h' -> contains '-f'
#   captagent_test: all checks passed
# W3 本地 CI（setup.sh + build_and_test.sh）PASS
# 探索期：./src/captagent -v → version: 6.4.4；-a 真实调用 pcap_findalldevs
```

## 交付物
| 文件 | 说明 |
|------|------|
| packaging/captagent-6.4.4-ohos-aarch64.tar.gz | 打包产物（bin/captagent + 14 模块 .so + etc 配置 + licenses） |
| reports/test-report.md | 测试报告（上游 0 可运行测试 + test_package 2 断言） |

## 注意事项
- 上游无集成测试（tests/ 只有 1 个孤儿源依赖 Check 框架），PR 中如实申报 0 个
- 真实抓包（pcap_findalldevs 等）在设备上需 root 权限，属运行环境限制
- commands.json `binary: false`（status=built 未发布，符合 ARCHIVE-SPEC 语义）
- E017：finish/close-archive 会把 conandata sources.url 重写成 file:// 本地路径，每次 finish 后、git add 前必须恢复官方 https URL 并删 conandata.yml.ghfast-bak

---

**编译结束**: 2026-08-31
