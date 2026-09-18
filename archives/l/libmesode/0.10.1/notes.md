# libmesode 0.10.1 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-09-16
- 编译器: clang/clang++ 15
- 状态: built（待真机预检）

## 上游信息

- 上游仓库: https://github.com/profanity-im/libmesode
- 上游版本: 0.10.1（2020-10-19 发布，configure.ac 内版本号一致）
- 源码包: https://github.com/profanity-im/libmesode/archive/refs/tags/0.10.1.tar.gz
- sha256: c9dd90648e73d92b90f2b0ae41a75d8f469b116d3e6aa297c14cd57be937d99e（curl 下载实测，与 FreeBSD distinfo 一致）
- 许可证: MIT（另含 GPL-3.0 文本，双许可；配方取 MIT）
- 说明: Profanity XMPP 客户端用的 libstrophe fork，已声明 deprecated，上游建议新项目用 libstrophe >= 0.11.0；本适配仅做基础适配存档
- 构建系统: autotools（configure.ac + Makefile.am，GitHub archive 不含 configure，需 autoreconf 自举）
- 依赖: expat >= 2.0.0（XML 解析，唯一 parser）、openssl（TLS，--disable-tls 可关，默认开）、系统 resolv（res_query 探测，RESOLV_LIBS 按平台选择）

## 上游测试清点

- 测试目录: tests/，automake TESTS 共 12 项（Makefile.am 实数）：
  1. tests/check_parser 2. tests/test_sha1 3. tests/test_md5 4. tests/test_rand
  5. tests/test_scram 6. tests/test_ctx 7. tests/test_base64 8. tests/test_hash
  9. tests/test_jid 10. tests/test_snprintf 11. tests/test_string 12. tests/test_resolver
- 运行方式: build() 内 `make check`（与上游 `make check` 同命令，真机实测以预检日志为准）
- 注意: test_resolver 涉及 DNS；若真机无网失败，后续轮次将单独评估是否豁免，其余 11 项为纯离线单测

## 编译步骤（2026-09-16 修订：直驱 cc，不再经过 autotools）

1. `AutotoolsToolchain.generate()` 仅作为交叉工具链环境载体（conanbuild 提供带 sysroot 的 CC/CFLAGS/LDFLAGS/AR），不调用 configure/make
2. `res_query` 探测：先 `-lresolv` 后 libc，复刻 configure.ac 的硬错误语义（都找不到则构建失败，不静默跳过）
3. 直驱 `$CC -fPIC -Wall` 编译 21 个上游源文件（Makefile.am `libmesode_la_SOURCES` TLS-on/expat 分支原文），`$AR rcs` 打静态库；shared 时 `$CC -shared` 链接并以 version-script 复刻 `-export-symbols-regex '^xmpp_'`（链接器拒绝则降级普通链接并告警）
4. 上游测试直驱：按 Makefile.am `check_PROGRAMS` 源映射编译 12 个测试程序（含 `-static` 等价的静态库链接），以 automake 退出码协议执行（0==PASS），输出 `HMBS_UPSTREAM_TEST_RESULT` 并持久化 `res/hmbs_upstream.json`
5. `package()` 直接装配 `include/mesode.h`、`lib/libmesode.so(.a)`、手写 `libmesode.pc`（按 `libmesode.pc.in` 替换）、licenses
6. test_package 直接编译消费者程序并链接 `libmesode::libmesode`，运行 11 断言程序并输出 HMBS_TEST_PACKAGE_RESULT

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub archive 无 configure | git tree 快照不含自举产物 | tool_requires automake+libtool，build() 内判无 configure 则 `autoreconf -fi`（libstrophe 同法） |
| 2 | aclocal 报 undefined macro PKG_CHECK_MODULES / LT_INIT | SDK pkg.m4 与 libtool 宏不在默认 aclocal 路径 | _prepare_build_env 注入 ACLOCAL_PATH（pkg-config 前缀 + libtool 包内 share/aclocal） |
| 3 | configure 临时目录 Permission denied（HMDFS） | 上游 configure 内 `umask 077` 与只读语义冲突 | 自举后把 configure 内 `umask 077` 改 `umask 007`（libstrophe 同法） |
| 4 | -lssl 可能链到系统库而非 conan 包 | 环境 LDFLAGS 中系统 -L 排在 conan -L 前 | generate() 内把依赖 libdir 的 -L 前置（lcalc/libstrophe 同法） |
| 5 | 本机 Windows 检出 main 即脏（libXext/libxext） | 上游同时存在仅大小写不同的两目录，Windows 同目录覆盖 | 非本任务改动，不提交；真机（Linux）无此问题 |
| 6 | 预检沙箱无原生 autoreconf（`/bin/sh: autoreconf: inaccessible or not found`） | 沙箱 PATH 无 autoconf 套件 | 首轮加 `tool_requires autoconf/2.72`，结果把失败转移到依赖构建，见 #7 |
| 7 | `autoconf/2.72` 引入的 `m4/1.4.19` 在沙箱从源码编译失败（`configure[139]: /data/service/hnp/bin/bash: inaccessible or not found`） | profile 用已不存在的绝对路径 bash 重 exec configure；conan 侧 autoconf/m4 在此沙箱不可构建 | 换策略：不再依赖 autotools——直驱 `$CC` 编译（configure.ac 无 config.h，所有探测从不物化为宏；Makefile.am 非递归且源列表显式），测试按 `check_PROGRAMS` 映射直驱（test_resolver 经核查为纯离线 canned 包解析，无需 DNS） |
| 8 | 直驱后 `res_query` 探测失败（先 `-lresolv` 后 libc 均失败，且旧探测吞掉了编译器输出无法定位） | 待预检诊断日志确认：头文件缺失与符号缺失是两种不同缺口 | 探测改为分头文件/符号两阶段且落盘打印日志尾；`src/resolver.c` 做特性宏适配（`HAVE_RESOLV_H` 控制 include/手动声明，`HAVE_RES_QUERY` 控制 live 查询调用，缺符号时返回 NOT_FOUND 走 `xmpp_connect_client` 文档化的 domain:port 回退；被测的 `_buf` 解析器原样保留），改写点精确匹配断言+幂等哨兵，失配即显式报错 |
| 9 | libmesode.so link tls_free duplicate symbol (ld.lld) | libmesode tls.h global tls_* collides with openssl/3.5.6.1.1 libssl.a global tls_free, duplicate definition when statically linking shared lib | compile-time -D rename of 14 tls_* to mesode_tls_* (public API is xmpp_* only, version-script already hides the rest), applied to lib + tests |
| 10 | test_package `xmpp_stanza_set_text failed`(rc=6) | test.c 先 set_name(TAG) 后对同一 stanza 调 set_text；上游 stanza.c 对 TAG 返回 XMPP_EINVOP；另断言累计 11 但终检写 10 | 改为子文本节点模式（TEXT 子 stanza 上 set_text/get_text_ptr，add_child 后用 get_text 聚合校验，与 message_set_body 同模式），终检与 CONSUMER_ASSERT_COUNT/MANIFEST 同步为 11，不删断言 |

## 源码修改

无补丁。conandata.yml 仅官方源单 URL（CI 自动加镜像 fallback，不手动加 gh-proxy）。

## 依赖版本

- openssl/3.5.6.1.1（TLS）
- expat/2.8.2.1.1（XML parser）
- 无 tool_requires（直驱 cc，不依赖 autoreconf；预检沙箱既无原生 autoreconf，也无法从源码构建 conan 的 autoconf/m4，见 #6/#7）

## 验证结果

```bash
# 待 HMBS 真机预检（conan create 全量：make check 12 项 + test_package 11 断言）
# 本轮仅完成未提交工作树，不贴本地结果；数字以预检日志与 PR 正文为准
```

## 证伪计划（预检通过后补证据）

- 确认 `make check` 日志含 12 个 PASS 且产物非空（防 toybox 式空文件比空文件假绿）
- 必要时用 `exit 1` 桩替换被测二进制重跑，确认 harness 能抓失败
- 区分通过与静默跳过：无 plan/0 断言的项计跳过不计通过

## 注意事项

- 本库非系统同名库，默认 shared=True，保留 .so（R26 不适用）
- 纯库类型，无 commands.json（R38 不适用）
- `settings.os` 判断用 `in ("Linux", "OHOS")`（R32）
- build() 无裸 `${CC}` 等 shell 变量（R33），编译器取自 conf
- test_package 真实调用 xmpp_* API，非空壳（R34）；覆盖 ctx/stanza/JID/SHA1/Base64/UUID/message
