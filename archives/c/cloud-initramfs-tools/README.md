# cloud-initramfs-tools

> initramfs-tools 云镜像扩展模块（overlayroot / growroot / rescuevol / dyn-netconf），纯 POSIX shell，无编译产物。

## 简介

`cloud-initramfs-tools` 是 Debian 云团队维护的 **Debian 原生包**（`debian/source/format = 3.0 (native)`，上游工程 `lp:cloud-initramfs-tools`），由**一个源包产出 4 个二进制包**（全部 `Architecture: all`）：

| 二进制包 | 作用 |
|---|---|
| `overlayroot` | 在只读根文件系统之上叠加 overlayfs（tmpfs / 块设备 / dmcrypt 三种后端），并提供 `overlayroot-chroot` 命令 |
| `cloud-initramfs-growroot` | 首次启动把根分区扩展到磁盘末尾（调用 `growpart`） |
| `cloud-initramfs-rescuevol` | 存在 `LABEL=RESCUE_VOL` 的分区时优先从该卷启动 |
| `cloud-initramfs-dyn-netconf` | 把 initramfs 期间配置过的网卡写成 `/run/network/interfaces` |

上游交付物是 initramfs-tools 的 **hooks**（`/usr/share/initramfs-tools/hooks/*`）与 **阶段脚本**（`init-top` / `init-bottom` / `local-bottom` / `local-premount`），加上配置片段、motd 片段、`overlayroot-chroot` 与 man 手册；上游 `Makefile` 无编译步骤，`install:` 目标仅用 `install(1)` 拷贝这些文件（实测 14 个文件）。

## OHOS 适配要点

1. **构建期 install(1) 可见性**：OHOS 的默认进程 PATH 含 `/system/bin`（其中提供 `install`），但交互 shell / 受限环境常裁剪该目录，此时上游 `make install` 报 `/bin/sh: install: inaccessible or not found` → `Error 127`。recipe 的 `build()` 会条件化生成一个指向平台 busybox `install` applet 的同名 shim（仅在 `which('install')` 为空时启用），使构建对 PATH 组成不敏感；使用 `-m 644` / `-m 755 -d` / `-m 644 -t` 等上游 Makefile 形式均已实测可用。
2. **脚本内工具解析**：busybox 1.37 含 `umount`/`chroot` 等 applet，但平台可能不暴露同名命令。补丁 `0001` 在 `overlayroot-chroot` 内加入 `xcmd()`：优先按原名调用（与上游行为逐字一致），原名缺失时回退 `busybox <applet>`。
3. **只读系统路径**：OHOS 的 `/etc` 与 `/tmp` 均为只读。随包配置落 `res/etc/overlayroot.conf`、`res/etc/update-motd.d/97-overlayroot`；`runenv_info` 导出 `OVERLAYROOT_CONF` 指向包内配置，`CLOUD_INITRAMFS_TOOLS_HOOKS` 指向 hooks 目录。
4. **权限归一化**：HMDFS 下 `install -m 755` 实测落地为 770（`-m 644` → 660）；断言以可执行位与内容字节一致为准。
5. **平台能力限制**：沙箱未放行 mount 族 syscall，真实 `umount`/`chroot <args>` 以 `SIGSYS`（rc=159）结束；`overlayroot-chroot` 的改挂载与 chroot 能力需特权 / initramfs 环境。

## 排除与替代

- 本包在 OHOS 上**没有 initramfs-tools 运行时**（无 `/usr/share/initramfs-tools/hook-functions`、无 `/scripts/functions`、无 `/conf`），hook 与阶段脚本的**主体逻辑**只能在其设计目标环境（initramfs 构建 / 启动）中行使；在 OHOS 上可行使的是 hooks 的 `prereqs` 协议、`overlayroot-chroot` 的解析与失败路径，以及全部交付物的语法/布局契约。
- Debian 侧由 `debhelper`（dh）驱动打包，本适配不使用 dh，改用上游 `Makefile` 的 `install:` 目标。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| （无强制第三方依赖） | — | W0 实测 `direct_forced=0`、`total_forced=0`；上游 `Build-Depends` 仅 `debhelper-compat (= 13)`（本适配未使用） |

运行期依赖均为 OS / 发行版工具（initramfs-tools、cloud-utils、util-linux、e2fsprogs、cryptsetup、systemd/udev 等），不属于可 `require` 的 Conan 三方库。

## 功能验证

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 上游入口协议（9 个）逐项真实执行
sh <pkg>/share/initramfs-tools/hooks/overlayroot prereqs           # → cryptsetup
sh <pkg>/share/initramfs-tools/scripts/init-top/cloud-initramfs-dyn-netconf prereqs  # → udev

# 打包 CLI
sh <pkg>/bin/overlayroot-chroot /bin/true    # 无 overlayroot 挂载 → rc=1，提示 Unable to find an overlayroot filesystem
```

test_package 套件：**16 用例 / 59 断言 / 全通过**（含 4 个鸿蒙特有用例），详见 `0.18.debian14/reports/test-report.md`。

## 参考

- [上游（Launchpad）](https://launchpad.net/cloud-initramfs-tools)
- [Debian 打包仓库（salsa，权威上游 VCS）](https://salsa.debian.org/cloud-team/cloud-initramfs-tools)
- [源码归档（salsa 标签 `debian/0.18.debian14`）](https://salsa.debian.org/cloud-team/cloud-initramfs-tools/-/archive/debian/0.18.debian14/cloud-initramfs-tools-debian-0.18.debian14.tar.gz)
