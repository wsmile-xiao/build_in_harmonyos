# libwebsockets 4.3.5 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-08-14
- 编译器: clang / clang++（Conan OHOS profile，ohos-aarch64）
- 状态: built（conan-verify 通过，未提交 release/upload CI，故不标记 published）
- 平台: OpenHarmony PC (aarch64)

## 编译步骤

```bash
# Conan 配方验证（含干净构建 + test_package 消费者测试）
conan create archives/l/libwebsockets/4.3.5 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -r=ohpcd --build=libwebsockets/4.3.5 -c tools.build:jobs=1
```

关键 CMake 选项：

- `LWS_WITH_SSL=ON`：启用 OpenSSL（依赖 openssl/3.5.6）
- `LWS_WITH_HTTP2=ON`、`LWS_WITH_CLIENT=ON`、`LWS_WITH_SERVER=ON`
- `LWS_WITHOUT_TESTAPPS=ON`、`LWS_WITH_MINIMAL_EXAMPLES=OFF`：包内不构建演示/测试程序
- `LWS_WITH_NETLINK=ON`、`LWS_WITH_IPV6=ON`
- `CMAKE_POLICY_VERSION_MINIMUM=3.5`：规避 CMake 策略版本问题

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 编译 linux/if_addr.h 时 sockaddr_storage 与 sys/socket.h 冲突 | OHOS 内核头与 musl libc 头同名类型冲突 | 补丁 0001：include 前 `#define sockaddr_storage __linux_sockaddr_storage`，include 后 undef |
| 2 | OHOS 编译 linux/netlink.h 时同样冲突 | 同上 | 补丁 0002：同样在 include 前重命名 |

## 源码修改

- `patches/0001-lib-core-net-client-sort-dns.c.patch`：lib/core-net/client/sort-dns.c，OHOS 平台头文件冲突修复（portability）
- `patches/0002-lib-roles-netlink-ops-netlink.c.patch`：lib/roles/netlink/ops-netlink.c，OHOS 平台头文件冲突修复（portability）

两个补丁均经 `patch --dry-run -p1` 在官方 v4.3.5 源码上验证可干净应用，无逻辑改动，仅为 OHOS 平台头文件兼容。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| openssl | 3.5.6 | LWS_WITH_SSL 必需；制品仓已发布 |

## 验证结果

```bash
# conan create（含 test_package 消费者测试）
# 退出码 0；test_package lws_consumer 运行通过全部 8 个断言
# 详见 test_package/MANIFEST.yml
```

上游测试说明：libwebsockets 4.3.5 上游无随包 CTest 自动测试（test-apps 为演示程序，api-tests 需单独以
`LWS_WITH_MINIMAL_EXAMPLES=ON` 构建且部分依赖网络）。本版本在 package 构建时关闭 minimal examples，
消费者验证由 test_package 的真实程序执行（见 test_package/MANIFEST.yml 与最终报告中的上游测试统计）。

## 历史占位归档修复

origin/main 中的历史占位归档存在以下问题，本 PR 已修复：

- 缺少 conanfile.py / conandata.yml / test_package（已补齐）
- manifest 中源码 URL 为本机 file:// 路径（已替换为官方 GitHub 归档 URL + 真实 SHA256）
- SHA256 为空（已填充）
- status 误标 published（已改为 built，直到远程制品仓真实发布）
- 依赖 openssl/3.0.0 未发布（已改用已发布的 openssl/3.5.6）

## 注意事项

- 本库是 ttyd 1.7.7（主任务 Issue #2148）的前置依赖，消费者可通过 Conan 直接 `self.requires("libwebsockets/4.3.5")` 使用。
- 不得将本归档标记为 published，除非 release/upload CI 已真实发布到制品仓。
---

**编译结束**: 2026-08-14 22:43
**最终状态**: built
