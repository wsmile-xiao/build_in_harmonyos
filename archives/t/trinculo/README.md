# trinculo

Trinculo 是 Luke Jostins 编写的多类别表型全基因组关联分析工具集（GWA
multinomial/ordinal logistic regression、贝叶斯模型选择与精细定位），
上游最后版本 0.96（2016-01，SourceForge 发行），Debian science 持续打包
至 0.96+dfsg-5（liblapack-dev 为唯一 Build-Depends）。

- 适配版本目录：`archives/t/trinculo/0.96/`（custom 单 TU 直编，CLI 应用，
  依赖 lapack/3.12.1）
- 源码锚定：Ubuntu 池 orig tarball（dfsg 重打包），sha256
  `51b73c31…b5767d` 与 ftp.debian.org / mirror.nodesdirect.com /
  old.kali.org 三镜像 + Debian 官方 `.dsc` PGP Checksums-Sha256 全等
  （四路 distinct=1）
- 上游页面：https://sourceforge.net/projects/trinculo/
- 知识沉淀：E709（SSTR 宏 rvalue dynamic_cast 的 clang 代差）、E711
  （Python2 测试驱动 py3 移植 + golden MD5 跨平台全等）、E712（PF7 +dfsg
  子串判据与 %2B 编码绕行 + SF urllib 403 双面取源），草稿见
  `knowledge/drafts/E709-draft-*`、`E711-draft-*`、`E712-draft-*`
