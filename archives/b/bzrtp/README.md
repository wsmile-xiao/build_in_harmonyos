# bzrtp

## 简介

bzrtp 是 Belledonne Communications 开源的 ZRTP 密钥协商协议实现
（RFC 6189），用于为 SRTP 会话协商加密密钥，是 Linphone 通话栈的组件之一。
库以 C 形态 API 对外提供服务，内部含 C++ 翻译单元，并可扩展支持后量子
（PQC）混合密钥协商。

## 功能特性

- 完整的 ZRTP 密钥协商状态机（Hello/Commit/DHPart/Confirm 等消息编解码）
- 多通道（multistream）与无缓存（cacheless）实现
- 基于 sqlite 的 ZID 缓存与密钥连续性（key continuity）
- GoClear/Clear ACK 消息支持
- PGP word list（B256）SAS 呈现
- 自带 30 个用例的 BCUnit 非回归测试（`bzrtp-tester`）

## OHOS 适配要点

- **同 train 依赖**：上游要求 `BCToolbox 5.3.0`，用制品仓的 `bctoolbox/5.3.115`
  满足；`find_package` 指向 bctoolbox 包内上游自带的 `BCToolboxConfig`
 （提供 `bc_*` 宏与 tester 组件目标）。
- **上游测试真实执行**：`ENABLE_UNIT_TESTS=ON` 构建 `bzrtp-tester`，
  在配方 `build()` 内以 `--resource-dir` 指向源码 `test/` 运行，
  CUnit `Run Summary` 分母必须等于审计值 30，否则判失败。
- **ZID cache 保持开启**：上游默认 `ENABLE_ZIDCACHE=ON`，
  `sqlite3/3.53.4` 为正式依赖；禁用会导致 2 个 zidcache 用例空转通过，
  本配方将其判为失败。
- **无平台补丁**：X25519/decaf 缺失由上游测试自行探测回退 DH3k；
  PQC 保持上游默认关闭（PostQuantumCryptoEngine 未发布）。
- **静态包带 C++ 运行时**：`shared=False` 时声明 `system_libs=["c++"]`，
  纯 C 消费者链接静态归档必需。

## 编译依赖

- bctoolbox 5.3.115（含 tester 组件）
- sqlite3 3.53.4（ZID cache）
- bcunit 5.3.113（仅测试用，不进入消费方依赖链）

## 运行依赖

消费静态库的应用需链接 bctoolbox 与 sqlite3（由 Conan 传递闭包自动处理）。

## 参考资料

- 官方仓库：https://gitlab.linphone.org/BC/public/bzrtp
- GitHub 镜像：https://github.com/BelledonneCommunications/bzrtp
- 协议：RFC 6189（ZRTP: Media Path Key Agreement for Unicast Secure RTP）
- 许可证：GPL-3.0-or-later（另有商业双许可）
