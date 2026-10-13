# dosfstools

FAT 文件系统工具集：`mkfs.fat`（格式化）、`fsck.fat`（一致性检查与修复）、
`fatlabel`（卷标读写），并由上游 `--enable-compat-symlinks` 提供
`mkfs.vfat` / `fsck.vfat` / `mkfs.msdos` / `dosfsck` / `dosfslabel` 等传统
别名，覆盖 SD 卡 / U 盘生态的 FAT12/16/32 卷管理场景。

Conan application 包：产物是 `bin/` 下的命令行工具，无库产物、无三方依赖
（仅 libc / musl）。消费者测试在**普通文件镜像**上执行 mkfs → fsck →
fatlabel 断言链（非特权即可运行；块设备与挂载面在本平台对非特权用户不可
用 —— `losetup`/`mount -o loop` 实测权限拒绝 —— 不属于本交付的断言面）。

- 上游: https://github.com/dosfstools/dosfstools
- 许可: GPL-2.0-or-later（源码 COPYING）
- 版本: 4.2（归档见 `4.2/`）
