# cgit-pink — OpenHarmony 编译档案

## 软件简介
cgit-pink 是 cgit 的维护型 fork，为 git 仓库提供快速的 Web 前端（CGI），用 C 编写，支持仓库浏览、log/diff/tree、快照下载、Atom 订阅与语法高亮过滤器。

## OHOS 适配要点
- 纯 Makefile 构建，复用树内 git 源码（按上游 Makefile 的 GIT_VER 2.36.1 解包为 `git/` 子目录，避免构建期网络下载）。
- `NO_LUA=1` 关闭可选 lua 探测，`NO_CURL=1` 沿用上游 cgit.mk 的默认设置。
- 编译器与 openssl/zlib 头库路径全部来自 Conan（conf 与 dependencies），不依赖 shell 环境变量（R33）。
- 不执行上游文档目标（asciidoc/a2x 在 OHOS 非必需）；`package()` 手工拷贝 `bin/cgit`、css/png 与 filters。
- 上游 `make test` 的 14 个 shell 集成测试在 `build()` 内完整执行。

## 依赖关系
- openssl/3.5.8.1（libcrypto/libssl）
- zlib/1.3.1（git 底层压缩）
- 构建期：make、sh/bash、perl（git 构建脚本所需）

## 参考资料
- [cgit-pink 上游](https://git.causal.agency/cgit-pink/)
- [cgit README 构建说明](https://git.zx2c4.com/cgit/tree/README)
