# libnftnl 1.3.1 适配笔记

## 编译环境
- 构建系统: Autotools
- 编译日期: 2026-09-10
- 编译器: clang 15.0.4
- 平台: HarmonyOS PC arm64
- 状态: built

## 编译步骤
使用 Conan `libmnl/1.0.5`，配置 `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos --disable-static --enable-shared`，并执行 `make` 与 `make check`。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.status: subs1.awk: Permission denied` | HMDFS 上 Autotools 的 `umask 077` 临时目录对当前进程不可写 | `0001-configure.patch` 改为 `umask 022` |
| 2 | `sockaddr_storage` 重定义 | OHOS `linux/socket.h` 与 `sys/socket.h` 同时定义该结构 | Conan 编译参数注入 `_UAPI_LINUX_SOCKET_H` 与 `__kernel_sa_family_t=sa_family_t` |
| 3 | `tcphdr.dest` 不存在 | OHOS SDK 使用标准字段 `th_dport` | `0002-examples-nft-rule-add.c.patch` |

## 源码修改
两个补丁均为平台兼容修复，无修改上游核心 API。

## 依赖版本
- libmnl/1.0.5

## 验证结果
- 上游 `make check`: 32/32 passed
- 消费者测试: 调用 `nftnl_table_alloc`, `nftnl_table_set_str`, `nftnl_table_get_str`, `nftnl_family2str`
---

**编译结束**: 2026-09-10 18:00
**最终状态**: published
