# tgl

Telegram API 与 MTProto 协议库（上游 https://github.com/vysheng/tgl ，快照 commit `ffb04cac`，
2016-03-23）。本目录跟踪赛事清单里的 `2.0.1-git20160323.ffb04cac` 版本。

## 功能概述

- MTProto 客户端协议栈：TL schema 驱动的查询与结构体编解码、DH 密钥交换、加密会话、
  消息与更新分发、binlog 与文件分片上传下载
- 内置 libevent 后端（`--enable-libevent`）提供网络与定时器，使库可独立使用
  （不加该选项时上游要求调用方自带 net/timers 实现）
- 公共头 `<tgl/tgl.h>` 提供状态管理（`tgl_state_alloc`）、peer / message 树、
  查询 API 与 TLS/加密辅助函数

## OHOS 适配

- 7 个补丁（详见 `2.0.1-git20160323.ffb04cac/notes.md`）：
  用制品仓 `tl-parser` 替代缺失的 git 子模块并补齐其两个头文件、新增 `install` 目标、
  去 `-Werror`、追加 `-UNDEBUG`（生成器依赖带副作用的 assert）、OpenSSL 1.1+ 不透明 RSA API、
  `tgl_peer_id_t` 完整初始化、HMDFS `pwd`/临时目录与 conftest 无法执行的平台适配。
- 静态交付：制品仓 `zlib/1.3.1` 为非 PIC 静态库，`libtgl.so` 无法链接，因此按 `static-library`
  只交付 `lib/libtgl.a`。
- 上游该快照不含测试套件，配方在 `build()` 内做审计留证，并补充消费者用例（12/12 通过）。

## 依赖关系

- 编译依赖：`openssl/3.5.6.1`、`zlib/1.3.1`、`libevent/2.1.13`；构建期工具 `tl-parser/0.0.0-git20210107.1933e76f`
- 运行依赖：`openssl`、`zlib`、`libevent`（共享或静态均可，由消费方决定）

## 参考资料

- 源码：https://github.com/vysheng/tgl
- TL 语法：https://core.telegram.org/mtproto/TL-tl
- 依赖的 TL 编译器：https://github.com/vysheng/tl-parser
