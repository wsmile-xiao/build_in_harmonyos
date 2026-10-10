# rio

**Diamond Rio PMP300 便携 MP3 播放器命令行管理工具**（The Snowblind Alliance (c) 1999）

`rio` 通过 PC **并口**（默认基址 `0x378`）与 Diamond Rio PMP300 播放器通信，管理其
板载 flash 存储：显示目录、上传/下载 MP3、删除文件、初始化（含坏块检测）、
调整播放列表顺序。

## 用法

```bash
rio [options]
```

| 选项 | 说明 |
|------|------|
| `-d` | 显示目录 |
| `-iy` / `-in` | 初始化（`-iy` 检查坏块，`-in` 不检查） |
| `-x` | 操作外部 flash |
| `-u <file...>` | 上传文件 |
| `-g <file>` | 下载文件 |
| `-f <playlist>` | 从文本播放列表上传 |
| `-z <file>` / `-za` | 删除文件 / 删除全部文件 |
| `-o "<n n n>"` | 指定新的播放列表顺序 |
| `-p <hex>` | 并口基址（默认 `0x378`） |
| `-v` | 详细输出 |
| `-di` / `-dt` / `-dr <n>` | 初始化 / 发送 / 接收 IO 延时 |
| `-h <pos> <size>` | 十六进制转储目录块 |

示例：

```bash
rio -p 0x278 -d
rio -iy -u *.mp3
rio -d -in -f playlist.txt
```

不带参数运行 `rio` 会打印版本横幅、全部开关及默认值。

## 构建

- 构建系统：纯 makefile（上游无 configure，适配补丁补齐了 `./configure --prefix=` 接口与 `install` 目标）
- 版本：1.07（1999 年发布），许可证 GPL-2.0-only
- 源码：`https://deb.debian.org/debian/pool/main/r/rio/rio_1.07.orig.tar.gz`

```bash
./configure --prefix=$HOME/usr/local
make
make install
```

## OHOS 适配

- **LP64 修正**：协议使用的 32 位整数由 `long` 改为 `int`（aarch64 上 `long` 为 64 位，
  会使序列化目录结构由 512 变成 516 字节）；`rio.h` 用 `static_assert` 在编译期锁定
  `CDirHeader`=512、`CDirEntry`=128、`CEnd512ByteBlock`=16 字节。
- **端口 I/O 后端**：aarch64 无 ISA I/O 端口空间，改为通过 `/dev/port` 的字节流接口
  访问端口寄存器（`pread/pwrite`，文件偏移即端口号）；x86 上仍使用原生
  `ioperm()+outb/inb`。`RIO_PORT_DEVICE` 可把该后端指向其它字节可寻址文件
  （诊断/非 `/dev/port` 暴露的硬件）。
- **libc 差异**：`sys_errlist[]` → `strerror(errno)`；去掉已被移除的 `<values.h>` 与
  内核内部头 `<linux/limits.h>`。
- **LP64 格式串**：修正 `app.cpp` 中 6 处 `%ld`/`%08lx` 与 `int` 实参不匹配的可变参数
  未定义行为。
- **构建**：makefile 改用 `$(CXX)/$(CXXFLAGS)`，去掉 `chmod +s`（HarmonyOS 拒绝
  setuid 可执行文件）。
- 无并口硬件/无 `/dev/port` 时，工具报
  `open( /dev/port ) failed, reason 'No such file or directory'` 并正常退出，不崩溃。
