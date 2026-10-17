# mbr

mbr 提供 `install-mbr`：IBM PC 兼容机的备用主引导记录（MBR）安装工具。MBR 本体用 8086 汇编（as86 方言）编写，汇编成 512 字节裸镜像后经 `xxd -i` 转成 C 数组，链接进 aarch64 宿主程序 `install-mbr`，因此工具本身与目标架构无关。

## Key Features
- 安装 MBR 引导扇区，并保留目标磁盘的分区表与磁盘签名区（440..509）
- 读取已有 MBR 的参数（版本、兼容版本、Y2K 修正、驱动器、默认分区、超时、启用分区、中断键）
- 参数化安装：`-d` 驱动器 / `-t` 超时 / `-p` 默认分区 / `-e` 启用分区 / `-i` 中断键 / `-y` Y2K 修正
- `-I` 从文件安装代码，`-k` 仅改参数，`-n` 空操作，`-f` 跳过安全检查
- 与 LILO 等其它引导器共存（兼容历史 1.0.x / 1.1.x 布局）

## Compiled Version
- **Version**: 1.2.2
- **Platform**: HarmonyOS (aarch64-unknown-linux-ohos)
- **Build System**: Autotools
- **Build-time tools**: dev86/0.16.21（as86/ld86）、xxd/9.1.0
- **Runtime dependencies**: 无（仅 libc）

## Notes
- `patches/0001`：上游 `%.s86: %.S86` 规则假定 `.S86` 与 `.s86` 是两个文件；HMDFS 大小写不敏感时 make 认为中间产物 `mbr.s86` 已存在（实际是源文件 `mbr.S86`），预处理配方被跳过、as86 直接汇编未预处理源码报 87 处 unbound label。中间后缀改为 `.i86`（产物字节不变）。
- 上游 `make check` 注册的 6 个用例中 4 个通过；`inst-1` / `inst-3` 断言的是 `NEW_FORMAT` 之前的旧磁盘布局（磁盘签名区 / 参数块），在任何平台都会失败，详见 `1.2.2/reports/test-report.md`。
- `install-mbr --version` 打印的上游版本串仍是 `1.2.1`（上游未随 1.2.2 更新该字符串）。
