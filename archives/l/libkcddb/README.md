# libkcddb

KDE CDDB 库：CD 音频元数据（CDDB/FreeDB/gnudb 协议）查询、提交与本地缓存。
提供 KCddb6 共享库（libKCddb6.so），是 audiocd KIO-slave（KDE 音频 CD 提取）
的核心依赖前置。

- 上游：https://invent.kde.org/multimedia/libkcddb
- 许可证：LGPL-2.0-or-later AND GPL-2.0-or-later

## HarmonyOS PC 适配说明

| 项 | 说明 |
|---|---|
| KIO 替换 | 上游 HTTP 查询/提交走 KIO::TransferJob；制品仓未发布 kio，替换为 Qt6::Network（QNetworkAccessManager），对外 API 不变 |
| kcmcddb 禁用 | KCM 系统设置面板依赖 KIO/KCMUtils/Solid（均未发布），BUILD_KCM=OFF 跳过；audiocd 依赖链不需要 |
| KCoreAddons 显式化 | `cdinfo.cpp` 用 `KStringHandler::perlSplit`（属 KCoreAddons），上游靠 KIO 传递获得；补丁显式 `find_package(KF6 ... CoreAddons)` 并 PRIVATE 链接 `KF6::CoreAddons` |
| 测试 | 上游注册 14 个测试：cdinfotest/cachetest 离线可测并纳入 CI；其余 12 个（http/cddbp/musicbrainz lookup/submit/sites）依赖外网服务器，CI 无网环境豁免（4 个 musicbrainz 用例上游在无 libmusicbrainz5 时自行 QSKIP） |

## 版本

- 26.04.3: built (2026-09-09)，源码包 <https://download.kde.org/stable/release-service/26.04.3/src/libkcddb-26.04.3.tar.xz>
- 26.04.0: built (2026-09-21)，源码包 <https://download.kde.org/stable/release-service/26.04.0/src/libkcddb-26.04.0.tar.xz>
  —— 与 26.04.3 相比，`libkcddb/` 源码与 `tests/` 逐字节相同，差异仅在 `po/` 翻译与 `kcmcddb/kcm_cddb.json`（kcmcddb 由 BUILD_KCM=OFF 关闭），故适配补丁与依赖代际完全一致
