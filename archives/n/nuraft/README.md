# NuRaft

C++ 实现的 [Raft 共识协议](https://raft.github.io/) 核心逻辑复制库，由 eBay 开源维护。
本仓库将其适配到 HarmonyOS PC（aarch64）平台。

## 功能

- Raft 核心：leader 选举、日志复制、集群成员变更（add_srv/remove_srv）、快照
- 网络层：基于 ASIO 的异步 RPC（vendored asio-1-24-0）
- 存储：`log_store` / `state_mgr` 插件接口，由使用者实现持久化
- 状态机：`state_machine` 接口，业务逻辑由使用者实现

## OHOS 适配要点

| 项 | 说明 |
|---|---|
| 构建系统 | CMake，非 WITH_CONAN 模式 |
| ASIO | vendored（asio-1-24-0，上游 prepare.sh 指定版本），standalone 模式 |
| SSL | 禁用（`DISABLE_SSL=1` → `SSL_LIBRARY_NOT_FOUND`），不依赖 openssl |
| Examples | 不编进产物（`BUILD_EXAMPLES=OFF`） |
| 测试 | 上游 CTest 10/10 通过；test_package 自带 3 节点集群冒烟 |

## 快速验证

```bash
conan create archives/n/nuraft/3.0.0 -pr:h ci/conan/profiles/ohos-aarch64 --build=missing
```

test_package 会在单进程内起 3 节点内存 Raft 集群，验证 leader 选举 +
日志复制 + commit index 前进。

## 版本

- 3.0.0（2026-09-12 适配）