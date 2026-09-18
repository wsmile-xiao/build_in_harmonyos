# devio

devio 是 John Bowler 2005 个人项目（MIT License）的 dd-like 块设备
读写工具，专为 mtd character 设备（jffs2 文件系统镜像、bootloader
备份、U-Boot 烧写等嵌入式场景）设计。与 `dd` 的关键差异：

- **非流式**：直接 mmap 到目标对象，不是 stream-based 读取
- **可指定访问区域**：精确控制偏移 + 长度
- **可输出数据位置**：read 模式支持打印从指定位置读出的字节
- **校验 /dump 友好**：支持 hex dump、buffer alignment

## 描述

devio 解决了 `dd if=/dev/mtd0 of=dump.bin bs=1M count=1` 类需求中**读
不可靠**的问题：在传统 dd 流式读 mtd 设备时，内核 buffer cache 和 mtd
子系统层之间的不一致会导致 read() 返回的字节数与请求不一致。devio
用直接 seek + read + retry 模式确保读到精确字节数，专门为 mtd
char 设备设计。

## 已编译版本

- 1.2 (2026-09-09, OHOS 适配版本)

## 特性

- 单 .c 文件（~1800 行 C 代码），MIT 许可
- 跨平台编译（Linux / OHOS aarch64 验证通过）
- 支持 block / character 设备读写
- 支持 mtd 子系统特定的 oob（out-of-band）数据
- 输出 hex dump 格式（位置 + 字节 + ASCII 三栏）

## 使用方法

```bash
# 读 256KB 块设备的 0x0 - 0x40000 区域
devio -i 0 -o 0 -l 0x40000 /dev/mtd0 dump.bin

# 写文件到 mtd 设备的 0x10000 - 0x20000
devio -i 0 -o 0x10000 -l 0x10000 /dev/mtd0 firmware.bin

# 读并 hex dump（验证写入是否正确）
devio -i 0 -o 0x10000 -l 0x100 /dev/mtd0 - | hexdump -C
```

## OHOS 适配

- devio.c 不依赖 autotools 生成的 config.h（直接 include 标准 POSIX
  头），conanfile 跳过 `autogen.sh + configure` 直接 `clang devio.c -o devio`
- 编译产出单可执行文件 `bin/devio`（约 30KB stripped）
- 所有系统调用（open/close/read/write/lseek/mmap/munmap）musl 全支持
- autotools 框架（configure/Makefile.in）随包携带但 build() 不调用
- **运行时限制**：devio 访问 `/dev/mtd0` 等块设备需要内核暴露
  设备节点 + 进程有权限；OH 内核默认配置可能不导出 mtd 字符设备
- conan 适配只验证 build 成功，runtime 行为取决于 OH 内核配置

## 典型使用场景

| 场景 | 命令 |
|------|------|
| 读 bootloader | `devio -i 0 -o 0 -l 0x40000 /dev/mtd0 uboot.bin` |
| 烧写 firmware | `devio -i 0 -o 0x100000 -l 0x80000 /dev/mtd0 firmware.bin` |
| 备份 jffs2 | `devio -i 0 -o 0 -l 0x800000 /dev/mtd4 jffs2.bin` |
| 验证写入（带 hex dump） | `devio -i 0 -o 0x10000 -l 256 /dev/mtd0 - \| xxd` |
