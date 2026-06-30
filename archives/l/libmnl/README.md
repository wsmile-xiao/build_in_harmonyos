# libmnl

## 简介

Minimalistic user-space library oriented to Netlink developers — 提供最小化的 Netlink 通信库，用于与 Linux/OHOS 内核 Netlink 子系统交互。

- 官网: https://www.netfilter.org/projects/libmnl/
- 许可证: LGPL-2.1-or-later
- 语言: C

## OHOS 适配

- 构建系统: autotools
- 当前编译版本: 1.0.5
- 平台三元组: `aarch64-unknown-linux-ohos`
- 需要的补丁: 3 个（config.guess / config.sub / configure HMDFS mktemp）
- 详见 `1.0.5/notes.md` 获取适配详情

## 依赖

- **必需依赖**: 无
- **可选依赖**: 无

## 功能验证

- pkg-config: `pkg-config --modversion libmnl` → 1.0.5 ✅
- 库链接: clang 编译链接 libmnl.so 成功 ✅
- 示例程序: 20 个示例全部编译通过 ✅
- 注意: 示例运行依赖内核 Netlink 模块，OpenHarmony 上部分内核模块可能未启用

## 交付物

| 版本 | 状态 | 预编译包 |
|------|------|---------|
| 1.0.5 | built | libmnl-1.0.5-ohos-aarch64.tar.gz (262KB) |

## 参考

- https://www.netfilter.org/projects/libmnl/
- libmnl API 文档: https://www.netfilter.org/projects/libmnl/documentation.html