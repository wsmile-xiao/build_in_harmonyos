# libktorrent

## 简介

libktorrent 是 KDE 的 BitTorrent 协议核心库，为 KTorrent 提供全部协议实现：bencode 编解码、torrent/magnet 元数据处理、peer wire protocol、DHT 分布式哈希表、uTP 传输协议、MSE 加密握手、磁盘 IO（含预分配）、tracker 与 UPnP 支持。产物为 KTorrent6 共享库。

## OHOS 适配（26.04.0）

- **构建系统**: CMake + ECM（KDE Frameworks）
- **依赖线**: qtbase/6.11.1 + KF6 6.26 线（karchive/kconfig/kcrash/ki18n/kio/solid 均取 6.26.0，与 kio 6.26.0 配方锚定线一致）
- **crypto 后端**: LibGcrypt（libgcrypt/1.12.2 + libgpg-error/1.55）——ohpcd openssl/3.5.6.1 为静态构建且不含 legacy provider 模块（ossl-modules 目录缺失），RC4 所需的 legacy provider 加载必败导致 bt::InitLibKTorrent() 返回 false；libgcrypt 原生提供 ARCFOUR（RC4）
- **关键补丁**: 0001-ohos-kiocore-only.patch
  - KIOWidgets → KIOCore + ConfigCore（ohpcd kio 包为 KIOCORE_ONLY 形态，KIOWidgets target 不存在；库内仅 3 处 widgets 专属调用：createDefaultJobUiDelegate / 2×uiDelegate()->showErrorMessage()，注释为 headless 空操作——KJob 仍通过 error()/errorText() 报错）
  - KIO::ERR_* 枚举来源改为直接 #include <KIO/Global>（原经 JobUiDelegate 链式包含）
  - httprequest.cpp 补显式 <QTcpSocket>（精简 qtbase 上传递包含不稳定）
  - 38 个 ecm_add_test 全部显式链接 Qt6::Gui（QTEST_MAIN 展开 QGuiApplication main 的确定性）
  - KTorrent6Config.cmake.in 补 find_dependency(KF6Solid/KF6I18n)——上游模板遗漏，任意平台消费者 include Targets 时会报 "KF6::Solid not found"（上游 bug）
- **测试**: 上游 38 个 ctest 全注册全执行全通过（100%）；test_package 消费者测试通过（bencode round-trip + SHA-1 + version API）

## 依赖

- 运行: qtbase, karchive, kconfig, kcrash, ki18n, kio, solid, boost, gmp, libgcrypt, libgpg-error
- 构建: ecm/6.26.0

## 版本

- 26.04.0 (2026-09-20)
