# libuio

Linux UIO（Userspace I/O）用户空间辅助库（上游：[missinglinkelectronics/libuio](https://github.com/missinglinkelectronics/libuio)，LGPL-2.1-or-later）。

通过 sysfs（`/sys/class/uio`）枚举 UIO 设备，提供设备名/版本/属性读取、内存映射（mmap）、8/16/32/64 位寄存器读写与 IRQ 阻塞读等 API；同时附带两个命令行工具：

- `lsuio`：列出系统 UIO 设备及其属性
- `readuio`：按偏移读取指定 UIO 设备的 32 位寄存器

无强制外部依赖（glib-2.0 为可选支持，本仓适配以 `--without-glib` 关闭）。上游 0.3.0 无测试套件（清点证据见 `0.3.0/test_package/MANIFEST.yml`）。

## 已适配版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.3.0 | built | 2026-09-19 完成前置适配，待真机/shadow CI 验证 |
