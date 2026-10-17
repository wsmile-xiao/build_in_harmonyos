# ncdc

NCurses 文本界面的 Direct Connect (DC / DC++) P2P 网络客户端。

## 功能概述

- 全屏 ncurses TUI，连接 DC hub、浏览用户列表与文件列表
- 支持多 hub 同时连接、私聊、公共聊天
- 基于 TLS（GnuTLS）加密传输
- 本地 SQLite 数据库缓存 hub/用户/下载队列状态
- 下载列表支持 zlib / bzip2 压缩传输
- 支持 GeoIP / libloc（可选，上游默认关闭）

## OHOS 适配

- 上游为 autotools 应用，发布 tarball 自带 `configure`/`Makefile.in`，零补丁。
- 上游 `Makefile.am` 无 `TESTS`/`check` 目标，**无测试套件**；故以真实二进制实跑
  `ncdc --version` / `ncdc --help` 自证：`--version` 打印 glib / gnutls / sqlite3
  的**编译期与运行期**版本，二者相等即证明运行期加载的是本配方打包的 conan
  制品，而非设备上的同名系统库。
- 依赖发现分两路（`PKG_CHECK_MODULES` + `AC_CHECK_LIB`），配方同时启用
  `PkgConfigDeps` 与 `AutotoolsDeps`；并手写 `glib-2.0.pc` / `gthread-2.0.pc`
  （glib 配方的 `pkg_config_name` 是聚合名 `glib-2.0-unofficial`）。
- `--without-geoip` / `--without-libloc` 显式关闭可选依赖，避免误探测宿主库。

## 依赖关系

编译依赖（均已发布 OHOS armv8 制品）：

| 依赖 | 用途 |
|------|------|
| ncurses/6.6 | TUI（ncursesw） |
| zlib/1.3.1.1 | `-lz`，压缩传输 |
| bzip2/1.0.8 | `-lbz2`，压缩传输 |
| sqlite3/3.49.1 | 本地状态数据库 |
| glib/2.84.0.2 | glib-2.0 + gthread-2.0 主循环 |
| gnutls/3.8.10 | TLS |

运行期仅需上述依赖的共享库（`bin/ncdc` 由 Conan runenv 的 PATH 提供）。

## 参考资料

- 官网/文档：https://dev.yorhel.nl/ncdc
- 源码下载：https://dev.yorhel.nl/download/ncdc-1.25.tar.gz
