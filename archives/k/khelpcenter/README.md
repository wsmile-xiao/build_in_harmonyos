# khelpcenter

KDE 帮助中心（KDE Gear 26.04，KF6/Qt6）。

上游仓库：https://invent.kde.org/kde/khelpcenter

本仓库的 OHOS PC（aarch64）适配交付 headless Xapian 文档检索栈：

- `libkhcdocmetainfo.so` — 文档元数据模型库（DocEntry / DocMetaInfo /
  DocEntryTraverser + kcfg 生成的 Prefs 配置类）
- `libexec/khc_xapianindexer` — 扫描 KDocTools 文档目录，把 *.cache.bz2
  文档缓存灌进 Xapian 全文索引
- `libexec/khc_xapiansearch` — 查询 Xapian 索引并按 searchhandler 协议输出
  HTML 片段

版本索引见 manifest.yaml；各版本适配细节见对应版本目录的 notes.md。
