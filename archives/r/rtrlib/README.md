# rtrlib

## 简介

rtrlib 是一个轻量级开源 C 语言库，实现了 RPKI/RTR 协议客户端（RFC 6810 / RFC 8210）、BGP 前缀源验证（RFC 6811）以及基于 ASPA 的路由泄漏检测，是 FRR 等 BGP 软件路由器实现 RPKI 功能的后端库。

- **上游版本**：0.8.0
- **许可证**：MIT
- **主页**：https://github.com/rtrlib/rtrlib

## 功能特性

- RPKI/RTR 协议客户端（TCP 传输，SSH 传输可选）
- 前缀源验证表（pfx_table，基于 trie）
- SPKI 表（路由器密钥维护，BGPSEC 所需）
- RTR 管理器（多缓存服务器故障切换）
- 自带命令行工具 `rtrclient` 与 `rpki-rov`

## 已适配版本

| 版本 | 状态 | 适配日期 | 构建系统 |
|------|------|----------|----------|
| 0.8.0 | built | 2026-09-15 | cmake |

## OHOS 适配

- 适配路径为基础适配：零外部依赖，SSH 传输默认关闭（`RTRLIB_TRANSPORT_SSH=OFF`），原因是 libssh 在制品仓中尚未发布，按 R36 不引入未发布依赖；如需 SSH 传输可将配方 `with_ssh` 选项置 true（届时需先发布 libssh）。
- `CMAKE_SYSTEM_NAME` 映射为 Linux，与仓库内同类 C 网络库做法一致。
- 上游 ctest 共注册 8 项测试，其中 `test_live_validation` 需实时联网访问公网 RPKI 缓存（rpki-validator.realmv6.org:8283），离线 CI/真机无法运行，构建中用 `ctest -E live_validation` 排除，其余 7 项真实执行。
- 上游 `tests/unittests` 下的 2 项 cmocka 单测需 `UNIT_TESTING=ON`（上游默认关闭），本次未启用，未引入 cmocka 依赖。
- 上游同时构建 `rtrlib`（共享）与 `rtrlib_static`（静态，仅测试链接用）两个目标，仅共享库被安装；包内 `bin/` 下的 `rtrclient` / `rpki-rov` 为上游默认构建的命令行工具，随包安装。

## 依赖

无外部依赖（默认选项）。可选依赖：libssh/0.11.4（仅 `with_ssh=True` 时）。

## 参考资料

- 上游仓库：https://github.com/rtrlib/rtrlib
- 项目官网：https://rtrlib.realmv6.org/
- 版本说明：https://github.com/rtrlib/rtrlib/releases
