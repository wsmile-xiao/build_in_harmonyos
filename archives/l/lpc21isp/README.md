# lpc21isp

**便携式命令行 ISP（在系统编程）工具**，用于 NXP LPC1000/LPC2000 系列及 Analog Devices ADUC70xx 微控制器

lpc21isp 通过串口（RS232 / COM 口）将 Intel HEX 或二进制固件烧录到 NXP LPC 系列及 ADI ADUC70xx 微控制器的 Flash 中，支持芯片检测、擦除、编程、校验及终端模式。由 Martin Maurer 开发，源码托管于 SourceForge。

## 用法

```bash
lpc21isp [Options] file[ file[ ...]] comport baudrate Oscillator_in_kHz
```

| 选项 | 说明 |
|------|------|
| `-bin` | 上传二进制文件 |
| `-hex` | 上传 Intel HEX 格式文件（默认） |
| `-term` | 烧录完成后启动终端 |
| `-termonly` | 仅启动终端（不烧录） |
| `-localecho` | 终端本地回显 |
| `-detectonly` | 仅检测 LPC 芯片型号（NXPARM） |
| `-debug0` ~ `-debug5` | 调试输出级别（0=静默，5=完整） |
| `-donotstart` | 烧录后不启动 MCU |
| `-try<n>` | 同步重试次数 |
| `-wipe` | 上传前擦除整个设备 |
| `-control` | 用 RS232 控制线引导（Reset=DTR，EnableBootLoader=RTS） |
| `-controlswap` | 交换 RS232 控制线（Reset=RTS，EnableBootLoader=DTR） |
| `-controlinv` | 反转 RTS/DTR 状态 |
| `-verify` | 每次写入后校验 Flash 数据 |
| `-logfile` | 终端输出记录到 lpc21isp.log |
| `-halfduplex` | 半双工串口通信（如 K-Line） |
| `-writedelay` | 串口写入后加延迟（兼容性） |
| `-ADARM` | 目标为 Analog Devices ADUC70xx |
| `-NXPARM` | 目标为 NXP LPC 系列（默认） |
| `-boothold` | 全程保持 EnableBootLoader 有效 |

示例：

```bash
lpc21isp test.hex com1 115200 14746
```

无参数运行时打印版本号与用法并以 exit(1) 退出，可用于 CLI 冒烟测试（不依赖硬件）。

## 构建

- 构建系统：纯 Makefile（`Makefile`，无 configure 脚本、无 `make check`/`install` 目标）
- 版本：1.97（2014-01-09 发布）
- 许可证：LGPL-3.0-or-later（README 声明，源码内含 lgpl-3.0.txt 与 gpl.txt）
- 源码：https://sourceforge.net/projects/lpc21isp/files/lpc21isp/1.97/

## OHOS 适配

- 上游 Makefile 用 `OSTYPE`/`uname` 做平台检测，OHOS 无 `_WIN32`/`__CYGWIN__`/`__APPLE__`/`__FreeBSD__` 且为 linux arm → 落入 `else` 分支 `COMPILE_FOR_LINUX`/`COMPILED_FOR "Linux"`，串口 termios 路径天然可用。
- 上游 Makefile 对非 Apple 平台硬编码 `-static`；OHOS 静态链接 libc 需 `libc.a`，本配方改为由 Conan Toolchain 管理 CFLAGS，去掉硬编码 `-static`，改用动态链接 musl（与仓库其他 CLI 工具一致）。
- `stricmp`/`strnicmp` 在 Linux 分支映射为 `strcasecmp`/`strncasecmp`（头文件已处理）。
- 无上游测试套件：Makefile 仅 `all`/`clean` 目标，无 `check`/`test`/`install`。
- 纯软件测试路径：无参数运行 → 打印版本 banner + 用法 → `exit(1)`，全程不触碰串口/硬件，可用于 CI。
- 硬件路径（`PerformActions` → `OpenSerialPort` → termios/ioctl + `NxpDownload` 与 MCU 通信）需真实 NXP 芯片 + 串口，CI 无法覆盖，仅在 test_package 中验证 CLI 启动/版本/参数解析。
