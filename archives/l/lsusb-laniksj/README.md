# lsusb-laniksj

lsusb command for macOS — 在 macOS 上模拟 Linux `lsusb` 的纯 Bash 脚本。

LanikSJ/lsusb 是一个单文件 Bash 脚本（445 行），通过解析 macOS
`system_profiler` 的文本输出，模拟 Linux lsusb 的设备列举、过滤（VID:PID、
bus:dev）与树状输出（`-t`）。上游无构建系统、无 libusb 依赖、无 USB/Linux
C API 调用——Homebrew 直接安装脚本到 bin。

## 与 usbutils（真 lsusb）的关系

| | lsusb-laniksj | usbutils（已有归档） |
|---|---|---|
| 实现 | 纯 Bash 脚本解析 system_profiler 文本 | C + libusb/libudev |
| 数据源 | macOS system_profiler | usbfs/sysfs |
| OHOS 上行为 | 无 system_profiler → 空设备列表、退出码对齐 Linux lsusb 语义 | 真实列举 USB 设备 |

在 HarmonyOS PC 上本包提供脚本语义的 lsusb（零补丁可运行）；需要真实 USB
设备列举时请使用 usbutils。

## Runtime Dependencies

- bash >= 4（脚本依赖 shopt extglob / here-string / getopts）
- （仅 macOS）system_profiler、sw_vers、ioreg — OHOS 上缺失时优雅降级

## Usage

```bash
lsusb            # 列出 USB 设备（无数据源时为空，退出 0）
lsusb -V         # 显示版本：lsusb for macOS 1.1.9
lsusb -h         # 用法帮助
lsusb -d 05ac:4500   # 按 vendor:product 过滤（无匹配退出 1）
lsusb -s 001:002     # 按 bus:dev 过滤
lsusb -t         # 树状输出
lsusb -v         # 透传 system_profiler 原始输出
```

## OHOS 适配

- 零源码补丁：所有 macOS 专有命令探测失败路径均优雅降级
- 必须用真 Bash 执行（`/system/bin/sh` 为 mksh，不支持 extglob）
- HMDFS 下显式 chmod 0o755 保证可执行位
- GitHub 直连不稳定时 conandata.yml 提供 gh-proxy 镜像 fallback

## 参考资料

- 上游仓库: https://github.com/LanikSJ/lsusb
- 项目主页: https://laniksj.github.io/lsusb/
- Homebrew formula: https://formulae.brew.sh/formula/lsusb-laniksj
