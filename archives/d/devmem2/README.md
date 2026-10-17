# devmem2

devmem2 是 www.lartmaker.nl/lartware/ 2004 年原创、后续由 VCTLabs 与
literming 等维护的极简内存读写工具。单 .c 文件 ~200 行，用于嵌入式
开发中读/写 MMIO 寄存器、GPIO、DMA 地址等物理内存。最初是为了
TI OMAP 系列芯片调试，后被 ARM 嵌入式社区广泛使用（BeagleBone、
Raspberry Pi 等）。

## 描述

devmem2 通过 mmap 将 `/dev/mem`（或用户指定的字符设备）映射到用户空间，
然后以 byte / halfword / word 三种宽度之一读/写指定物理地址。
支持 verbose 模式（hexdump 风格显示内存区域）和 read-only 模式。

与 BusyBox `devmem` 类似但更完整：
- 显式指定访问宽度（b/h/w）
- 支持任意长度（连续读/写区域）
- 输出 hexdump 格式
- 可指定其他设备文件（不限于 /dev/mem）

## 已编译版本

- 0.2 (2026-09-09, OHOS 适配版本，literming fork)

## 特性

- 单 .c 文件（~200 行 C 代码），Makefile 直接 make
- 跨平台编译（Linux / OHOS aarch64 验证通过）
- GPL-2.0 许可
- 无运行时依赖（除 libc：mmap/munmap/open/close/printf）
- 支持 byte / halfword / word 三种访问宽度
- 可读写任意对齐/非对齐地址

## 使用方法

```bash
# 读取 word（默认 32/64-bit）从物理地址 0x12345000
devmem2 0x12345000

# 读取 byte
devmem2 0x12345000 b

# 读取 halfword
devmem2 0x12345000 h

# 写入 word
devmem2 0x12345000 w 0xDEADBEEF

# 读 32 字节区域（hexdump 风格）
devmem2 0x12345000 32

# 写 32 字节（hexdump 风格）
devmem2 0x12345000 32 0x31

# 显式指定设备文件
devmem2 --file /dev/mem 0x12345000

# 只读模式
devmem2 --read-only 0x12345000
```

## OHOS 适配

- 编译时无特殊 flag：musl + clang 直接 make，Makefile 默认 CFLAGS
- mmap / open / close / read / write 在 musl 全部支持
- **运行时限制**：默认 `/dev/mem` 在 OH 内核不一定导出给普通进程；
  需要在内核开启 `CONFIG_STRICT_DEVMEM=n` 或在特权 shell 中运行
- conan 适配只验证 build 成功，runtime 行为取决于 OH 内核配置
- 单可执行文件 `bin/devmem2`，运行时无动态库依赖（除 libc）

## 典型使用场景

| 场景 | 命令 |
|------|------|
| 读 GPIO 寄存器 | `devmem2 0x44e07000` |
| 写 GPIO 引脚（BeagleBone） | `devmem2 0x4804c134 w 0x1F` |
| 读 DMA 描述符地址 | `devmem2 0x4A300000 64` |
| 读 SoC 唯一 ID 寄存器 | `devmem2 0x44E10600 16` |
