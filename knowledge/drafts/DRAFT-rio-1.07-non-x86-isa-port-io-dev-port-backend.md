# DRAFT — 无 ISA I/O 端口空间的架构（aarch64/OHOS）上移植 x86 端口 I/O 程序

**来源**：rio 1.07（Diamond Rio PMP300 并口管理工具，1999）HarmonyOS PC 适配
**日期**：2026-09-29
**状态**：DRAFT（待主编审核归档编号）

## 问题

rio 的协议栈通过并口 3 个寄存器（数据 `base+0`、状态 `base+1`、控制 `base+2`，默认 `0x378`）
与播放器通信，原实现依赖 x86 专有的 `ioperm()` + `outb()/inb()` + `<sys/perm.h>` / `<asm/io.h>`
（读状态口还被当作微秒级延时用）。在 HarmonyOS PC（aarch64 + musl）上：

| 项 | OHOS 实际情况 |
|---|---|
| `<sys/perm.h>` | 不存在（x86 glibc 专有） |
| `<asm/io.h>` | 不存在 |
| `<sys/io.h>` | **存在但是空壳**（只 include `features.h` 与空的 `bits/io.h`），`ioperm/outb/inb` 全部未声明 |
| ISA 端口空间指令 | aarch64 不存在 |

编译期首个错误：`rio.cpp:69:12: fatal error: 'sys/perm.h' file not found`。

**关键陷阱**：不能用 `__has_include(<sys/io.h>)` 探测端口能力 —— OHOS 上该头存在但为空，
探测结果为假阳性；必须按架构判（`__i386__` / `__x86_64__`）。

## 方案（对比得到的最优解）

按架构分派端口后端，**不引入任何平台宏**（`patches/` 中无 `__OHOS__`，R8/PF5 合规）：

- x86（`__i386__`/`__x86_64__`）：保留原生 `<sys/io.h>` + `ioperm()` + `outb/inb`，行为逐字不变；
- 其余架构（含 aarch64/OHOS）：改用 `/dev/port` 的**字节流接口**——该字符设备字节可寻址、
  文件偏移即端口号，`pread/pwrite` 单字节即完成端口读写，无需内联汇编；
- `Set()` 阶段用 `open("/dev/port", O_RDWR)` 的成败充当“端口能力/权限”探测，失败按原有
  `CRIO_ERROR_IOPRERM` 上报并附 `strerror()` 文案，**优雅降级不崩溃**；
- 端口设备路径可通过 `RIO_PORT_DEVICE` 指向任意字节可寻址文件（诊断 / USB-并口桥 / 测试替身），
  使该后端在无并口、无 `/dev/port` 的机器（含 CI）上也能被**真实执行并按字节断言**，
  否则这段代码在 CI 上是永不被执行的死代码。

## 验证（HarmonyOS PC 真机，2026-09-29）

- `make CXX=clang++`：`0 error`（仅 3 条上游原有 `-Wsign-compare` 告警）
- G0 clean-verify：pristine tarball + 6 补丁上 `./configure && make && make install` 全通
- conan create（ohos-aarch64）：G0-G4 全绿
- 消费者测试 21/21（功能 6 + 鸿蒙特有 15），其中：
  - 无 `/dev/port`：`open( /dev/port ) failed, reason 'No such file or directory'`，未被信号终止；
  - 测试替身 `RIO_PORT_DEVICE=<file>`：`Set()` 通过 → 进入设备探测 → `device not found`，
    且端口映像文件被扩展到 891 字节、偏移 `0x378=0xa0`（数据口）/ `0x37a=0x04`（控制口），
    证明 `pwrite` 端口偏移寻址在 aarch64 上真实可用。

## 适用面

任何用户态直接读写 ISA 端口的程序：并口/串口外设工具、DOS 时代硬件工具、
`inb/outb` 型驱动辅助程序、工业 I/O 工具。

**不适用**：内存映射 I/O（`/dev/mem`、`mmap`）、经内核驱动或 `libusb`/`libgpiod` 的访问。
