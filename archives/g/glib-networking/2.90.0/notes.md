# glib-networking 2.90.0 适配笔记

## 概述
GLib 官方 TLS 后端实现（GIO 模块），桥接 OpenSSL。为 libsoup3 http2 测试链提供真实 TLS
后端（替代 OHOS 上 glib 的 GDummyTlsBackend 空实现）。Meson 构建，依赖 glib/2.88.3
（共享版，ohpcd 已发布）与 openssl/3.5.8.1。

## 版本说明
- 任务头写 version 2.90，GNOME 官方目录 LATEST-IS-2.90.0，tarball 实际为
  glib-networking-2.90.0.tar.xz，SHA-256 与 download.gnome.org 一致
  （83a75e3d9c36b66ee86d3281c2fc997816101968a5126ba322b2acb9a74dd8c0）。
- conandata.yml 使用官方 HTTPS URL。

## 关键适配点
1. **依赖选型**：glib/2.88.3（ohpcd 共享二进制，仅依赖 libc.so）而非 glib2/2.88.0
   （ohpcd 仅发布静态版）。GIO 模块与消费进程必须共享同一 glib 类型系统；静态 glib2
   会导致 "cannot register existing type" 双份注册冲突。
2. **pc 修复**：PkgConfigDeps 生成的 gio-2.0.pc 缺 giomoduledir 变量（meson.build 断言）；
   复制 glib 包真实 .pc 修 prefix 并前置 PKG_CONFIG_PATH。共享 glib 内嵌
   proxy-libintl/zlib/pcre2，pc 中 Requires/Requires.private 对应 .pc 不生成，须剥离。
3. **libintl.h include**：gi18n-lib.h 无条件 include <libintl.h>，显式声明
   proxy-libintl/0.5 依赖并注入其 include 目录。
4. **codesign 保护（libsoup3 同源铁律）**：meson.install() 清理 DT_RUNPATH 改写 .so
   内容，OHOS loader 校验 .codesign 哈希失配 → dlopen Permission denied。package()
   用 build 目录原始链接产物覆盖打包后的 libgioopenssl.so。
5. **测试运行时库路径**：meson test 直接运行 OHOS 二进制，LD_LIBRARY_PATH 注入
   glib 包 lib 目录（共享 glib 仅依赖 libc.so，无传递库路径需求）。

## TLS 后端生效验证（任务核心证据）
- **GDummy 对照**：未加载 glib-networking 时 g_tls_backend_get_default() 返回
  GDummyTlsBackend（空实现，http2 测试 0 执行根因）。加载本库模块后：
- **真实后端确认**：test_package 输出 `backend type: GTlsBackendOpenssl`、
  `GTlsClientConnection type: GTlsClientConnectionOpenssl`，g_tls_backend_supports_tls()=true。
- **进程级 TLS 连接复验**：本地 TCP socket 对 + GTlsClientConnection 握手，对非 TLS
  对端返回真实后端错误 "wrong version number"，证明模块代码路径实际执行（GDummy
  短路不会到达握手）。test_package RESULT: 10 passed, 0 failed。

## 上游测试完整枚举台账（tls/tests + proxy/tests）

### 源码声明（可复制枚举：用户测试源内 g_test_add*/g_test_add 注册项）
| 源文件 | g_test 注册声明数 | 说明 |
|--------|------------------|------|
| tls/tests/certificate.c | 29 | 其中 2 个 pkcs11 用例在 `#if HAVE_GNUTLS_PKCS11` 内 |
| tls/tests/file-database.c | 11 | |
| tls/tests/connection.c | 43 | 其中 client-auth-pkcs11 1 个在 `#if HAVE_GNUTLS_PKCS11` 内 |
| tls/tests/dtls-connection.c | 9 | 上游 meson.build 注释禁用（issue #49 未修复） |
| proxy/tests/environment.c | 3 | proxy 后端全 disabled，未实例化 |
| proxy/tests/gnome.c | 3 | proxy 后端全 disabled，未实例化 |
| **source_declared_total** | **98** | |

### 当前 OHOS 配置（openssl 后端，其余禁用）实际实例化
| 构建目标（meson test 注册项） | 实例化用例数 | 执行结果 |
|------------------------------|-------------|----------|
| certificate-openssl | 27（29 − 2 pkcs11 gnutls-only） | 27 ok / 0 fail |
| file-database-openssl | 11 | 11 ok / 0 fail |
| connection-openssl | 42（43 − 1 pkcs11 gnutls-only） | 42 ok / 0 fail |
| connection-openssl-tls1.2（TLS1.2 变体重跑） | 42 | 42 ok / 0 fail |
| **configured_executable_total / executed_passed_total** | **80 / 80** | 执行项次 122/122 ok |

### 双口径统计
- **80/98 (81.6%)**：executed_passed_total / source_declared_total（18 项未实例化：
  dtls 9 上游禁用 + proxy 6 后端禁用 + pkcs11 3 gnutls-only 条件排除）
- **80/80 (100%)**：当前配置可执行集合通过率（certificate 27 + file-database 11 +
  connection 42 独立用例全过；connection-tls1.2 为同批 42 用例的 TLS1.2 重跑，
  共 122 项次，全部 exit 0）

### 逐项映射
- certificate.c 29 声明 → 27 经 `BACKEND=openssl`/`-DBACKEND_IS_OPENSSL` 预处理与
  `#if HAVE_GNUTLS_PKCS11` 排除 2 → certificate-openssl 目标 → meson 注册项
  glib-networking:certificate-openssl → testlog.txt 27 ok。
- file-database.c 11 → 无条件宏排除 → file-database-openssl → 11 ok。
- connection.c 43 → 排除 client-auth-pkcs11 1 → connection-openssl → 42 ok；
  meson 对 connection 程序另注册 -tls1.2 变体（G_TLS_OPENSSL_MAX_PROTO=0x0303），
  同一 42 用例 TLS1.2 重跑 42 ok（testlog 含 # SKIP 注释项：output-stream-close
  openssl 1.1.1 不支持、tls-unique 不支持，均为上游 SKIP 语义，计入 ok）。
- dtls-connection.c 9 → meson.build 注释禁用（issue #49）→ 无构建目标 → 未实例化。
- proxy/tests 6 → environment_proxy/gnome_proxy/libproxy 均 disabled →
  proxy_test_programs 为空 → 未实例化。

### 运行命令（证据）
- meson test：`meson test -v -C <builddir> --timeout-multiplier=16`（conan create
  build() 内自动执行）
- testlog：`<conan cache>/p/b/glib-*/b/builddir/meson-logs/testlog.txt`，122 ok / 0 fail
- test_package：`conan test` 输出 10 PASS / 0 FAIL，TLS 后端生效全部断言通过

## 依赖发布状态
glib/2.88.3（shared，ohpcd 已发布）、openssl/3.5.8.1、pcre2/10.47、libffi/3.5.2、
zlib/1.3.2、proxy-libintl/0.5 全部已在 ohpcd 有 recipe/二进制，无依赖缺失阻塞。

## R02 复验记录（分支修正 feat/glib-networking-2.90.0）
- R01 已交付，CI R40 分支名失败（分支须含包名-版本号 glib-networking-2.90.0）；
  R02 改为 feat/glib-networking-2.90.0 后重新构建交付。
- 配方/源码/依赖与 R01 一致（复制复用），conan create 成功（exit 0），
  test_package 10/10（GTlsBackendOpenssl + 进程级 TLS 握手真实错误
  wrong version number），上游 4 suite 122 项次 ok / 0 fail（testlog：
  certificate-openssl 27、file-database-openssl 11、connection-openssl 42、
  connection-openssl-tls1.2 42）。
- 双口径统计不变：80/98（81.6%）源码口径、80/80（100%）配置可执行口径。
---

**编译结束**: 2026-09-13 17:32
**最终状态**: built
