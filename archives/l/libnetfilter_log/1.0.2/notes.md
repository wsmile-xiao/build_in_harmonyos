# libnetfilter_log 1.0.2 适配笔记

## 编译环境
- 构建系统: autotools（release tarball 自带 configure，build-aux/ 存放 config 侧脚本）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos，/data/service/hnp/bin，ohos-sdk 26）
- conan 2.29.1，profile `ci/conan/profiles/ohos-aarch64`（build==host 原生构建）
- 依赖: libmnl/1.0.5、libnfnetlink/1.0.2（均已发布 OHOS 二进制，conan list 实证）
- 状态: built（conan-verify 全绿）

## 编译步骤

1. `conan create archives/l/libnetfilter_log/1.0.2 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`（经 `ohc-run.py conan-verify`）
2. 关键 configure 参数：`--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`（本包 config.guess 不识别 OHOS，显式三元组绕过猜测）、`--enable-static --disable-shared`
3. `make -j1`；上游无测试套件（无 tests/ 目录），如实记录 0，不执行 make check
4. package() 内 ELF 自签（llvm-objcopy + binary-sign-tool，默认静态时无 .so 为空操作）
5. 消费者测试：裸 clang 编译 `test_consumer.c` → `test_consumer`，链接 libnetfilter_log 真实调用公开 API

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `cannot guess build type` | 本包 config.guess 不识别 OHOS 宿主 | 显式传 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`（经验汇总 §12.1），配合补丁 2 放行三元组 |
| 2 | config.sub 报 `Invalid configuration 'aarch64-unknown-linux-ohos'` | 2020 年版 build-aux/config.sub 不识别 ohos 三元组 | 移植补丁 `patches/0002-config-sub-ohos.patch`：参数校验后短路放行 `aarch64-*-linux*`/`aarch64-*-ohos*`（a52dec/0.7.4 同款手法） |
| 3 | `redefinition of 'sockaddr_storage'`（linux/socket.h × musl sys/socket.h） | OHOS sysroot 的 bionic 式 uapi 头与 musl 双重定义（E091/E119 家族） | 配方内联 `CPPFLAGS=-D_UAPI_LINUX_SOCKET_H -D__kernel_sa_family_t=sa_family_t`：抑制内核版头并以 musl 已有别名补齐 netlink.h 的依赖（E119 macro-guard-skip-header 方法的 CPPFLAGS 应用形态） |
| 4 | `redefinition of 'nfnetlink_groups'`（依赖兼容头 × sysroot uapi nfnetlink.h） | 抑制 sysroot socket.h 后，同一 TU 内依赖包自带 linux_nfnetlink.h（无守卫）与 sysroot nfnetlink.h 再冲突 | `CPPFLAGS` 追加 `-D_UAPI_NFNETLINK_H` 抑制 sysroot 版（依赖兼容头内容等价），并以补丁 `patches/0003-include-order-libnfnetlink-first.patch` 调整 3 个 TU 的包含顺序保证符号先定义 |
| 5 | configure 报 `PKG_CHECK_MODULES 找不到 libnfnetlink` | autotools 依赖发现走 pkg-config | generate() 增加 `PkgConfigDeps(self).generate()`（经验汇总 §12.1） |
| 6 | 消费者测试 `nflog_open()` 返回 NULL（errno=EACCES） | OHOS 内核策略禁止非特权进程打开 NETLINK_NETFILTER 协议套接字（python 探针实测 EACCES，协议已编译但被策略拦截） | 平台能力边界：测试保留 API 调用与编译/链接/装载验证，深度运行时断言（bind_group/合成报文解析）在策略放行的环境下自动执行，本机记录环境事实 |

## 依赖版本

- libmnl/1.0.5（归档已有）
- libnfnetlink/1.0.2（归档已有）

## 测试统计（五维账本）

- `N_static`：**0**（上游源码树无 tests/ 目录、无测试套件，如实记录）
- `N_registered` / `N_executed`：**0**（同上；消费者测试另列）
- 未执行分类：0（上游本无测试）
- `N_consumer`：**1** 个消费者程序 `test_consumer`——合成 NFULNL_MSG_PACKET netlink 报文驱动 `nflog_handle_packet` 分发与属性解析（open/callback_register/bind_group/handle_packet/get_prefix/get_indev/get_outdev/get_physindev/get_payload/close 共 10 项断言，断言失败非零退出）。本机环境 NETLINK_NETFILTER 被平台策略拒绝（EACCES，python socket 探针留证），深路径 10 断言在策略放行环境自动执行；本机执行已验证 API 调用链与编译/链接/装载。

## 知识库使用记录

- E386（HMDFS getcwd/shell 路由）+ 经验汇总 §12.38①：configure 内联 env 前缀路由（abx/0.1 先例）
- E011/E114 + 经验汇总 §12.1：config.status umask 077 临时目录受控改写
- E091/E119（sockaddr_storage 双重定义 / macro-guard-skip-header）：CPPFLAGS 抑制内核头 + 别名补齐
- a52dec/0.7.4 合入补丁：config.sub 短路放行手法
- §12.1：PKG_CHECK_MODULES → PkgConfigDeps
- B 判定：**hit**——主要适配点均命中既有条目（E386/E011/E114/E091/E119）或已合入先例（a52dec/abx），无新增机制，按路径 A 申报

## 验证结果

- `ohc-run.py conan-verify libnetfilter_log 1.0.2`：G0/G1/G2 全部 PASS（报告 reports/conan-verify-report.md）
- 消费者测试：编译/链接/运行通过（本机环境边界逐项记录，见上）
- E017 防回归：conandata.yml URL 保持官方形态 `https://ftp.netfilter.org/pub/libnetfilter_log/libnetfilter_log-1.0.2.tar.bz2`，sha256 `e3f408575614d849e4726b45e90c7ebb0e6744b04859555a9ce6ec40744ffeea` 与实测一致
---

**编译结束**: 2026-09-22 02:57
**最终状态**: built
