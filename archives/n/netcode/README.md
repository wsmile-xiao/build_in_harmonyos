# netcode — UDP 上的安全 client/server 协议

> 专为实时多人游戏设计的轻量安全连接协议，基于 UDP 提供连接管理、
> 加密签名包、connect token 鉴权、防重放与防放大攻击。

## 简介

netcode（mas-bandwidth/netcode，BSD-3-Clause）用 C99 实现，核心为
`netcode.c` / `netcode.h` 两个文件，加密依赖自带的 libsodium 子集
（`sodium/sodium.c`），无任何外部依赖。支持 IPv4/IPv6、单/双栈 socket、
loopback 连接、包 tagging（Wi-Fi 降抖）与连接超时/断开语义。

v1.4.3 为补丁版本：`netcode_generate_connect_token` 对
`num_server_addresses` 增加运行时界限检查（此前仅 assert，
Release 下 `-DNDEBUG` 会编译掉）。

## OHOS 适配要点

- CMake 原生构建：`NETCODE_BUILD_TESTS=ON` 跑上游套件，
  `NETCODE_SYSTEM_SODIUM=OFF` 使用自带 sodium（零外部依赖，免 R36 依赖发布）。
- 上游套件为单个 ctest（`netcode_test`），内含 46 个 `RUN_TEST`，
  部分为真实 UDP 建联测试，需真机回环网络可用。
- 上游测试 Runner 持久化到包内 `res/upstream-test`，使 `test_package`
  在 `conan create` 缓存命中时仍能重跑取证。
- 非 R26 系统同名库，默认静态构建；`netcode.h` 无导出宏，Linux/OHOS 下
  共享构建可用，Windows 下上游不支持共享构建。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| （无） | — | 加密与协议实现全部自带 |

## 功能验证

```bash
# 消费者测试（test_package 自动执行）
test_netcode   # 版本宏、地址解析/比较、默认配置、connect token 生成与越界拒绝
ctest -V --output-on-failure   # 上游 46 项
```

## 参考

- [上游仓库](https://github.com/mas-bandwidth/netcode)
- [协议标准 STANDARD.md](https://github.com/mas-bandwidth/netcode/blob/main/STANDARD.md)
- [v1.4.3 发布说明](https://github.com/mas-bandwidth/netcode/releases/tag/v1.4.3)
