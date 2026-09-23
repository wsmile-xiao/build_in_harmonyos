# DRAFT-glib-networking-2.90.0-tls-backend-bridge — OHOS 上 GLib 仅有 GDummyTlsBackend，以 glib-networking GIO 模块桥接真实 TLS 后端

- 触发事件：glib-networking 2.90.0 适配（libsoup3 http2 测试链恢复）
- 路径：Path B（知识库扩展）
- 编号：DRAFT-glib-networking-2.90.0-tls-backend-bridge

## 现象

OHOS 上 glib 自带 GDummyTlsBackend 是空实现：`g_tls_backend_get_default()`
返回 GDummyTlsBackend，`g_tls_backend_supports_tls()` 返回 FALSE。依赖 glib
TLS API 的库（libsoup3 http2 等）上游测试以 `if(!tls_available) return 0;`
短路，全部注册后 0 执行（libsoup3 http2 实测 35 项注册、0 项执行）。

## 根因

1. OHOS 上 GLib 缺少官方 TLS 后端模块：GLib 自带 GDummyTlsBackend
   （TLS 空实现），真实 TLS 能力由 glib-networking 项目以 GIO 模块形式
   （gioopenssl.so / giognutls.so）提供，该模块在 OHOS 上未被适配/安装。
2. GIO 模块是 dlopen 进消费进程的，必须与主程序共享同一 glib 类型系统。
   glib2/2.88.0 在 ohpcd 仅发布静态版；若模块与主程序各持一份静态 glib，
   GObject 类型系统双份注册 → `cannot register existing type`。
   因此必须消费**共享** glib（ohpcd 已发布 glib/2.88.3 shared）。
3. OHOS loader 校验共享库 .codesign 段内嵌哈希与文件内容一致性。
   meson.install() 会清理 DT_RUNPATH 并改写 .so 内容（libsoup3 已反复实证），
   哈希随之失配 → dlopen `Permission denied`。package() 必须用 build 目录
   原始链接产物覆盖打包后被改写的模块 .so。

## 修复

1. Meson 构建 glib-networking 2.90.0，openssl=enabled 单后端，
   gnutls/libproxy/gnome_proxy/environment_proxy 全部 disabled。
2. 依赖共享 glib/2.88.3 + openssl/3.5.8.1（均 ohpcd 已发布）+ proxy-libintl/0.5
   （显式声明以解析 libintl.h include）。
3. PkgConfigDeps 生成的 gio-2.0.pc 缺 giomoduledir 变量（meson.build 断言），
   复制 glib 包真实 .pc 修 prefix 并前置 PKG_CONFIG_PATH；共享 glib 内嵌
   proxy-libintl/zlib/pcre2，剥离 pc 中 Require 链。
4. package() 用 build 原始 libgioopenssl.so 覆盖 meson.install 改写产物
   （保 .codesign 哈希一致）。
5. 测试与消费者以 GIO_EXTRA_MODULES / GIO_MODULE_DIR 指向模块目录，
   LD_LIBRARY_PATH 指向共享 glib 库目录。

## 验证

- conan create 通过；上游 4 个 meson test 条目（certificate/file-database/
  connection/connection-tls1.2）122 项次 ok、0 fail（80/98 源码口径、
  80/80 配置可执行口径）。
- test_package 10/10：backend type GTlsBackendOpenssl、
  GTlsClientConnectionOpenssl、进程级 TLS 握手对非 TLS 对端返回真实后端错误
  `Error reading data from TLS socket: wrong version number`。
- GDummyTlsBackend 对照：未装模块时返回 GDummy，装后返回 GTlsBackendOpenssl。

## 适用边界

OHOS 上一切依赖 glib TLS API（g_tls_backend_get_default / GTlsConnection /
GTlsCertificate）且需要真实 TLS 能力的库或应用均可复用：libsoup3（http2 测试
恢复）、curl、libxml2、gtk 等。反例：仅用 G_DUMMY 后端即可满足的库不需要此方案。

## 查重

- similar_to：E285（audio Null backend 默认空实现限制上游测试——空后端域相通，
  但领域与解法不同：音频补 loopback vs 本方案安装真实 TLS 后端模块）
- caused_by：OHOS 缺 GLib 官方 TLS 后端模块
- prerequisite_of：libsoup3 http2 上游测试恢复
- conflicts_with：无
- 七轴结论：exact/causal/trigger/solution 四轴未命中，combination/boundary/
  test_migration 三轴为新增差异 → new_draft（Path B）