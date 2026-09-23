# cycfx2prog

## 简介

CycFX2Prog 是一个给 Cypress EZ-USB FX2 / FX2LP（Cypress 8051 + USB 控制器）写固件
的命令行工具。它把 8051 固件（Intel HEX 文件）通过 USB 下载到芯片 RAM，可以复位或
启动 8051，并提供了 bulk / control 端点的收发命令用于通用 USB 协议测试。

产物为单个命令行工具：`bin/cycfx2prog`。

## 功能概述

- 设备选择：`-d=BUS.DEV` 按总线/设备号选择，`-id=VV.PP[.N]` 按 VID/PID/序号选择；
  默认找第一个未配置的 FX2（`04b4:8613`）
- `--list`：列出总线与设备，并标注未配置的 FX2
- `--help` / `--version`：帮助与版本
- 8051 控制：`reset`（拉低复位）、`run`（拉高复位启动）、`prg:FILE`（下载 Intel HEX
  固件，下载前自动复位）
- 内存访问：`set:ADR,VAL`、`dram:ADR,LEN`
- 端点通信：`dbulk:EP,L[,N]`（bulk 读并 hexdump）、`sbulk:EP,STR`（发字符串）、
  `fbulk:EP,FILE[,CS]`（发文件或 stdin，可指定分块大小）、
  `bench_bulk:EP,L[,CS]`（吞吐测试）、`altif:[IF]`（切换 alt 接口）、
  `ctrl:TYPE,REQUEST[,VALUE[,INDEX]]`（零长度 control 消息）
- `delay:NN`：毫秒级延时

## 使用方法

```sh
cycfx2prog --list                    # 列出总线/设备，标注未配置 FX2
cycfx2prog --version                 # 打印版本
cycfx2prog prg:firmware.ihx run      # 下载固件并启动 8051
cycfx2prog -id=04b4.8613 prg:f.ihx   # 指定 VID/PID 后下载
cycfx2prog dram:0,64                 # dump RAM 前 64 字节
cycfx2prog sbulk:2,hello             # 向 EP2 发 "hello"
```

## OHOS 适配

- **构建系统**：makefile。上游是手写 Makefile，没有 configure，目标只有
  `all/clean/distclean/dist`，也**没有 install 与 check/test 目标**；配方因此不用
  `make install`，而是 `make -j1 CC=<profile clang> CFLAGS=... LDFLAGS=...` 之后显式
  安装 `bin/cycfx2prog`。
- **上游 Makefile 的 flags 必须用命令行变量传**：`CFLAGS`/`LDFLAGS` 在上游 Makefile
  里是 `=` 赋值，同名环境变量会被 makefile 的赋值覆盖，只有 make **命令行变量**能盖过
  它。配方把 `GnuToolchain` 的 cflags/defines（defines 需自行补 `-D` 前缀）与依赖的
  `-I/-L/-l` 拼进命令行变量，其中字符串宏
  `-DCYCFX2PROG_VERSION=\"0.47\"` 必须写两级反斜杠转义：值先经 makefile 展开、再由
  执行 recipe 的 shell 解析一次，只写一级转义会在第二层被剥掉引号，宏静默退化成浮点
  常量（`-Wformat` 会报 `format specifies type 'char *' but the argument has type
  'double'`，版本行打印出垃圾值）。
- **依赖**：上游用 libusb-0.1 API（`#include <usb.h>`、`-lusb`）。OHOS 没有 libusb-0.1
  本体，但 `ohpcd` 已发布 `libusb-compat/0.1.7`（默认静态、`fPIC=True`，提供
  `include/usb.h` 与 `lib/libusb.a`）与 `libusb/1.0.27`（`shared=True`，提供
  `libusb-1.0.so.0`）。配方 `requires("libusb-compat/0.1.7")`，链接 `-lusb -lusb-1.0`，
  最终产物 `DT_NEEDED` 为 `libusb-1.0.so.0` 与 `libc.so`。**不需要任何 stub、空实现或
  平台条件编译**（R8 无豁免）。
- **无补丁**：源码用 OHOS clang 15 原样编译通过，`patches/` 不存在。
- **上游测试**：0.47（2009 年发布）不带任何测试文件，Makefile 也没有 check/test 目标，
  按可审计台账记为上游 0（既不是 PASS 也不是 SKIP）。`test_package/` 补 33 个消费者
  视角用例，覆盖 CLI 契约与真实 libusb 运行路径。
- **硬件与软件的可验证边界**：`--help`/`--version` 不触碰 libusb；`--list` 会真正调用
  `usb_init()`/`usb_find_busses()`/`usb_find_devices()`（经 libusb-compat 落到
  libusb-1.0 的 linux_usbfs 后端），在无 USB 设备的环境里仍返回 0；所有"找不到设备"的
  错误路径都要求退出码 1。需要真实 FX2 芯片的下载/端点路径无法在 CI 覆盖。
- **运行方式**：只用 stdio / libusb，不访问 `/tmp`、不读 locale、不需要特权配置；设备
  访问由 libusb 后端决定，属运行时环境问题而非构建问题。

## 依赖关系

- 编译依赖：`libusb-compat/0.1.7`（→ `libusb/1.0.27`）、profile 中的 clang 15.0.4
- 运行依赖：`libusb-1.0.so.0`、`libc.so`（OHOS musl）

## 参考资料

- 官方项目页（源码与发布 tarball）：https://www.triplespark.net/elec/periph/USB-FX2/software/
- 上游作者：Wolfgang Wieser（wwieser@gmx.de）
- 许可证：GPL-2.0-only（源文件头声明 "GNU General Public License version 2"；发行
  tarball 内不含 COPYING 文件）
