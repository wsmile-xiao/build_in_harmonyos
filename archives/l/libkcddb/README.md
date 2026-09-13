# libkcddb

KDE CDDB 库：CD 音频元数据（CDDB/FreeDB/gnudb 协议）查询、提交与本地缓存。
提供 KCddb6 共享库（libKCddb6.so），是 audiocd KIO-slave（KDE 音频 CD 提取）
的核心依赖前置。

- 上游：https://invent.kde.org/multimedia/libkcddb
- 源码包：https://download.kde.org/stable/release-service/26.04.3/src/libkcddb-26.04.3.tar.xz
- 许可证：LGPL-2.0-or-later AND GPL-2.0-or-later

## HarmonyOS PC 适配说明

| 项 | 说明 |
|---|---|
| KIO 替换 | 上游 HTTP 查询/提交走 KIO::TransferJob；制品仓未发布 kio，替换为 Qt6::Network（QNetworkAccessManager），对外 API 不变 |
| kcmcddb 禁用 | KCM 系统设置面板依赖 KIO/KCMUtils/Solid（均未发布），BUILD_KCM=OFF 跳过；audiocd 依赖链不需要 |
| 测试 | 上游注册 13 个测试：cdinfotest/cachetest 离线可测并纳入 CI；其余 11 个（http/cddbp/musicbrainz lookup/submit/sites）依赖外网服务器，CI 无网环境豁免 |
