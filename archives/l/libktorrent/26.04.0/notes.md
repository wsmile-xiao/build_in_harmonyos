# libktorrent 26.04.0 — HarmonyOS PC (OHOS aarch64) 适配笔记

## 概况

- 上游：KDE Gear 26.04.0 libktorrent（https://invent.kde.org/network/libktorrent，tag v26.04.0 两镜像一致 30aec256）
- 源码：KDE release-service 官方 tarball https://download.kde.org/stable/release-service/26.04.0/src/libktorrent-26.04.0.tar.xz（sha256 4c7ef4b7416fcedf9d1ca8b759cae8ee0cd4254dca80e3978753399445dcf008）
- 依赖线：qtbase/6.11.1 + KF6 6.26 线（kio/6.26.0 为锚，全部五框架 6.26.0 均已发布）+ ecm/6.26.0
- 状态：conan create 全绿；上游 38 测试 100% 通过；test_package 通过

## 适配决策

1. **KIOWidgets 裁剪（核心决策）**：ohpcd kio/6.26.0 是 KIOCORE_ONLY 形态（KIOGui/KIOWidgets/KIOFileWidgets 不构建——其依赖 kbookmarks/kjobwidgets/kiconthemes 6.26 不在基线，kio 6.26.0 notes 补丁 0001-0004）。libktorrent 库内 KIOWidgets 实际用量：
   - src/torrent/job.cpp 构造 setUiDelegate(KIO::createDefaultJobUiDelegate())——widgets 弹窗
   - src/diskio/deletedatafilesjob.cpp / movedatafilesjob.cpp 各一处 uiDelegate()->showErrorMessage()
   其余 KIO 用量（Job/file_move/del/storedGet/CopyJob/MetaData/ERR_* 35 处）全是 KIOCore。补丁：链接改 KF6::KIOCore + KF6::ConfigCore（KSharedConfig 头在 kconfig，原本由 KIOWidgets 传递）；三处 widgets 调用注释化（KJob 无 delegate 时 error()/errorText() 照常携带错误信息）。
2. **KIO::ERR_* 来源**：JobUiDelegate 头删除后 ERR_USER_CANCELED（job.cpp/singlefilecache.cpp）失去链式包含来源，补 #include <KIO/Global>（kio 包 include/KF6/KIOCore/KIO/Global 实存）。
3. **crypto 后端 LibGcrypt（第二个关键决策）**：初版用 OpenSSL（上游默认 Auto 优先）。实测 10 个测试（全部调 bt::InitLibKTorrent() 的）在 initTestCase 失败：InitCryptoBackend() 调 OSSL_PROVIDER_try_load("legacy")——RC4 在 OpenSSL 3.x 移入 legacy provider，而 ohpcd openssl/3.5.6.1 是静态构建、无 ossl-modules/legacy.so，加载必败。切 USE_CRYPTO_BACKEND=LibGcrypt（libgcrypt/1.12.2 的 GCRY_CIPHER_ARCFOUR 原生支持 RC4，rc4encryptor.cpp 有完整 #elif 分支），38/38 全过。**先例警示**：后续依赖 libktorrent MSE 加密的消费者应确认 crypto 后端为 LibGcrypt 构建。
4. **libgpg-error 依赖**：gcrypt.h #include <gpg-error.h>。libgcrypt 配方虽有 transitive_headers=True 的 libgpg-error 声明，但 FindLibGcrypt 模块只解析 gcrypt.h 一层；显式 requires libgpg-error/1.55 + CMAKE_CXX_FLAGS 注入其 include。
5. **QTcpSocket 显式 include**：src/upnp/httprequest.cpp 用 QTcpSocket 但原靠传递包含（QNetworkReply 链）——精简 qtbase 上不稳定，补显式 #include <QTcpSocket>。
6. **38 测试全部链接 Qt6::Gui**：QTEST_MAIN 对 QObject 测试展开 QGuiApplication main 的条件是 TU 见到 QtGui 头——依赖 include 顺序不可靠（实测 streamingchunkselectortest/datacheckertest 链接失败），全量 12 个 tests/CMakeLists 的 ecm_add_test 统一补 Qt6::Gui（顶层 find_package(Qt6) 同步加 Gui 组件）。
7. **KTorrent6Config.cmake.in 上游 bug 修复**：KTorrent6Targets.cmake 的 INTERFACE_LINK_LIBRARIES 含 KF6::Solid/KF6::I18n，但上游 Config 模板只 find_dependency(KF6Archive/KF6Config/KF6KIO)——消费者 find_package(KTorrent6) include Targets 时 "KF6::Solid not found"（任意平台都会踩，非 OHOS 特有）。补两个 find_dependency。
8. **test_package 消费者桥接**：conan CMakeDeps 生成小写 boost::boost / libgcrypt::libgcrypt，而 KTorrent6 INTERFACE 用大写 Boost::boost / LibGcrypt::LibGcrypt——test_package CMakeLists 建 INTERFACE IMPORTED 桥接两类大小写（消费者同理）。
9. **KDE 先例复用**：ECM_MODULE_PATH 注入 / conan_cmakedeps_paths.cmake 手写（qtbase+KF6 全 cmake_find_mode=none）/ KF_SKIP_PO_PROCESSING / max-page-size=0x1000 / LD_LIBRARY_PATH 注入 / 绝对 DT_NEEDED 兼容符号链接（kgoldrunner 26.04.0 / audiocd 26.04.3 全套先例）。
10. **上游测试执行**：OHOS musl loader 对相对 DT_NEEDED（测试二进制 NEEDED ../../../bin/libKTorrent6.so）按 cwd 字面解析——库复制到 build 树对应位置 + 全依赖链 LD_LIBRARY_PATH + QT_QPA_PLATFORM=offscreen 后 38/38 全过（总耗时 11.2s）。

## 补丁（1 个）

| # | 补丁 | 目的 |
|---|------|------|
| 0001 | 0001-ohos-kiocore-only.patch（20 文件） | KIOWidgets→KIOCore+ConfigCore、ERR_* 头来源、QTcpSocket 显式 include、38 测试补 Qt6::Gui、Config.cmake.in 补 find_dependency、crypto 后端切 LibGcrypt 相关联动 |

## 测试统计（申报口径）

- **上游注册测试数 N = 38**（src/*/tests/CMakeLists.txt ecm_add_test 实注册：bcodec 2, datachecker 1, dht 2, diskio 2, download 2, magnet 1, mse 1, net 3, peer 4, torrent 3, util 5, utp 12）
- 实际执行 38 个，**38 通过 0 失败 0 跳过（100%）**
- test_package（消费者测试，鸿蒙特有）：1/1 通过（bencode round-trip / SHA-1 / version API / PeerIDPrefix）

## 构建产物

- lib/libKTorrent6.so（+ KTorrent6Config.cmake / KTorrent6ConfigVersion.cmake / KTorrent6Targets.cmake）
- include/libktorrent/（bcodec/datachecker/dht/diskio/download/interfaces/magnet/mse/net/peer/torrent/tracker/upnp/util/utp + version.h 等）

## 给后续版本的提示

1. KF6 6.27+ 若 kbookmarks/kjobwidgets 6.26+ 发布，kio 可去 KIOCORE_ONLY，届时 KIOWidgets 补丁可回退。
2. openssl 包若未来构建 legacy provider（ossl-modules/legacy.so），crypto 后端可回 OpenSSL（需 OSSL_MODULES_DIR 环境变量指向）。
3. KTorrent6Config.cmake.in 的 find_dependency 缺失是上游 bug，已在本仓补丁修复；升级版本时核对上游是否已修（invent.kde.org/network/libktorrent）。
4. KDE Gear 26.08+ 若 QTEST_MAIN 展开规则变化，Qt6::Gui 链接补丁段需复核。
