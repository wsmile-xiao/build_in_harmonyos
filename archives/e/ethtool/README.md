# ethtool

## 简介

Utility for examining and tuning Ethernet device parameters — 查询和配置网络接口（尤其是有线以太网设备）的驱动参数和硬件设置。

- 官网: https://mirrors.edge.kernel.org/pub/software/network/ethtool/
- 许可证: GPL-2.0
- 语言: C

## OHOS 适配

- 构建系统: autotools
- 当前编译版本: 6.15
- 平台三元组: `aarch64-unknown-linux-ohos`
- 需要的补丁: 1 个（configure HMDFS mktemp 权限修复）
- 依赖: libmnl/1.0.5（netlink 接口支持）

## 功能验证

- ethtool --version: ✅ version 6.15
- make check: ⚠️ test-cmdline 3 cases fail (environmental: no network devices)
- Conan test_package: ✅ passed (ethtool --version)

## 依赖

- **必需依赖**: libmnl/1.0.5（netlink 接口，默认启用）

## 参考

- https://mirrors.edge.kernel.org/pub/software/network/ethtool/
