# qemu for HarmonyOS PC

QEMU 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南与测试记录。

## 概述

QEMU 是通用机器模拟器与虚拟化器。在鸿蒙 PC 上它的价值不只是"又一个模拟器"：
本仓已有的交叉工具链（如 `gcc-11-cross`，目标 `arm-none-eabi`）能**编译链接**
ARM 目标程序，却**无法执行**产物——宿主既没有 AArch32 兼容层，也没有 ARM
模拟器。装上本包后：

- `qemu-arm` / `qemu-aarch64`（user mode）→ 直接运行 ARM/AArch64 Linux 可执行文件；
- `qemu-system-arm` / `qemu-system-aarch64`（system mode）→ 运行裸机镜像、
  内核与完整系统，配上包内 `share/qemu/` 的 ARM/AArch64 UEFI 固件即可引导；
- `qemu-img` → 磁盘镜像创建/转换/检查。

因此本包是"ARM 目标程序在鸿蒙 PC 上可执行"这条链路的最后一环。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | qemu |
| 版本 | 9.2.4 |
| 下载地址 | https://github.com/qemu/qemu/archive/refs/tags/v9.2.4.tar.gz |
| 官方文档 | https://www.qemu.org/docs/master/ |
| 许可证 | GPL-2.0-or-later |

> 下载源说明：`download.qemu.org` 与各镜像站的 `/qemu/` 路径在本机实测均不可达
> （连接超时或 404），GitHub tag archive 实测可达（39.85 MB，约 2.8 MB/s，
> gzip 魔数正确）。该 URL 同时在 CI 的镜像改写白名单内。

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.12.0 |
| 架构 | aarch64 |
| 编译器 | clang 15.0.4 (LLVM) |
| 构建系统 | qemu 自带 configure + meson/ninja |

## 编译步骤

```bash
# 1. 取源（也可交给 conan source）
curl -L -o qemu-9.2.4.tar.gz \
  https://github.com/qemu/qemu/archive/refs/tags/v9.2.4.tar.gz
sha256sum qemu-9.2.4.tar.gz   # c60f39779f3958152cf181db7aa33cce361a075f727a910679bbc3e3815f156f
tar xzf qemu-9.2.4.tar.gz

# 2. 依赖（全部来自 ohpcd 制品仓）
conan install --requires=glib/2.84.0 --requires=pixman/0.46.4 \
  --requires=zlib/1.3.1 --requires=libfdt/1.7.2 \
  --requires=libslirp/4.9.3 --requires=capstone/5.0.7

# 3. 配置（out-of-tree；只建 ARM 系目标）
./configure --prefix=<install> \
  --target-list=arm-softmmu,aarch64-softmmu,arm-linux-user,aarch64-linux-user \
  --enable-fdt=system --disable-docs --disable-guest-agent \
  --disable-werror \
  --disable-gtk --disable-sdl --disable-vnc --disable-xen --disable-brlapi \
  --disable-spice --disable-glusterfs --disable-libssh --disable-curl \
  --disable-libnfs --disable-vhost-net --disable-rdma

# 4. 编译与安装
ninja -C build
ninja -C build install
```

实际以 `archives/q/qemu/9.2.4/conanfile.py` 为准；上述命令即该配方
`build()`/`package()` 的执行内容。

## 依赖

| 依赖 | 版本 | 作用 |
|------|------|------|
| glib | 2.88.0 | QEMU 主库（必需） |
| pixman | 0.46.4 | 显示/像素运算 |
| zlib | 1.3.1 | 镜像与压缩路径 |
| libfdt | 1.7.2 | 设备树（flattened device tree） |
| libslirp | 4.9.3 | `-netdev user` 用户态网络 |
| capstone | 5.0.7 | monitor 反汇编 |

## 使用示例

```bash
# 运行 ARM Linux 可执行文件（user mode）
qemu-arm ./hello_arm

# 启动 ARM 虚拟机（system mode，配包内 UEFI 固件）
qemu-system-arm -M virt -m 256M \
  -bios <package_folder>/share/qemu/edk2-arm-code.fd \
  -nographic

# 创建磁盘镜像
qemu-img create -f qcow2 disk.qcow2 1G
```

## OHOS 适配要点

- **ELF 签名**：鸿蒙拒绝执行未签名 ELF，`package()` 对 `bin/` 下所有宿主可执行
  文件执行 `binary-sign-tool sign -selfSign 1`（与 `gcc-11-cross` 同一约定）。
- **libfdt 探测方式**：QEMU 用 `cc.find_library('fdt')` 而非 `dependency()`，
  必须把 libfdt 的 include/lib 目录显式传入 `--extra-cflags`/`--extra-ldflags`，
  仅靠 pkg-config 不足。
- **libfdt 依赖来自制品仓**：`dtc` 在制品仓无匹配，但 `libfdt/1.7.2` 已发布，
  故无需另建前置包。
- **目标集裁剪**：默认 `--target-list` 会构建 30+ 个目标，本适配只保留 ARM 系
  （system + user），既覆盖用途又避免数倍构建时间。
- **数据目录**：`pc-bios/` 固件随包安装到 `share/qemu/`（安装后不保留
  `pc-bios/` 层级，固件直接位于 `share/qemu/` 直属，另有 `firmware/`、
  `keymaps/` 子目录）；消费者按包目录定位，即
  `<package_folder>/share/qemu/edk2-arm-code.fd`。

## 版本索引

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 9.2.4 | built | 2026-09-27 | 本 PR 交付（ARM 系 system + user，`arm/aarch64` softmmu 与 linux-user） |
| 11.1.1 | built | 2026-09-22 | 由另一 PR 交付并已合入 main（`riscv64-softmmu`）；软件级清单在冲突解决时一并登记 |
