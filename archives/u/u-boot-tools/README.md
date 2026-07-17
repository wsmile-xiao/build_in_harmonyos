# U-Boot Tools (u-boot-tools)

U-Boot 引导加载程序的主机端工具集，包含用于创建、检查和操作
U-Boot 引导镜像的实用程序。

## 包含的工具

| 工具 | 用途 |
|------|------|
| mkimage | 创建 U-Boot 镜像文件 |
| dumpimage | 从 U-Boot 镜像中提取文件 |
| mkenvimage | 生成 U-Boot 环境二进制镜像 |
| fdtgrep | 设备树（FDT）内容过滤 |
| fit_info | FIT 镜像信息查询 |
| fit_check_sign | FIT 镜像签名验证 |
| envcrc | U-Boot 环境 CRC 计算 |

## 版本

- v2026.07 — 上游最新稳定版本（2026-07-06 发布）
- uprev 策略：跟随上游 U-Boot 版本

## 官方资源

- 上游源码: https://github.com/u-boot/u-boot
- 官方发布: https://ftp.denx.de/pub/u-boot/
- 许可证: GPL-2.0+

## 适配说明

u-boot-tools 编译方法：
1. `make sandbox_defconfig HOSTCC=clang -j1` — 生成 sandbox 主机工具配置
2. `make tools-only HOSTCC=clang HOSTLDSHARED="clang -shared" -j1` — 编译主机端工具
