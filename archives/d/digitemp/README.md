# DigiTemp (digitemp)
> 1-Wire 温度传感器读取工具，支持 DS9097/DS9097U 串口适配器

## 简介

DigiTemp 是 Brian C. Lane 开发的 1-Wire 总线工具，用于读取 Dallas/Maxim
DS1820/DS18S20/DS18B20 等 1-Wire 温度传感器。它通过串口适配器（DS9097、
DS9097U）或 USB 适配器与传感器总线通信，可批量读取总线上所有传感器温度，
输出原始/摄氏度/华氏度格式，并被 RRDtool、MySQL、Nagios 等脚本集成。

本包构建两种串口适配器版本：`digitemp_DS9097`（简单串口适配器）与
`digitemp_DS9097U`（带 DS2480B 芯片的串口适配器）。上游标注为 BROKEN 且依赖
libusb 的 `ds2490`（USB）目标不在本包范围内。

## OHOS 适配要点

- 上游 Makefile **没有可用的 `install` 目标**（其依赖不存在的 `digitemp` 目标），
  打包阶段由配方直接复制二进制与 man page，因此产物路径为 `bin/`、`share/doc/`、
  `share/man/man1/`。
- 编译器通过 `tools.build:compiler_executables` 注入（`make CC=<clang>`），
  不依赖 shell 环境变量，保证 CI 干净环境可复现。
- 上游源码未做任何修改（无补丁）；产物为 aarch64 ELF 可执行文件。
- 实际读取温度需要真实的 1-Wire 适配器与串口设备；无硬件环境下可运行的路径为
  命令行契约、`.digitemprc` 配置解析与串口错误处理。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libc | 系统自带 | 串口访问（termios）与文件操作，无第三方依赖 |

## 功能验证

```bash
# 显示用法与版本
digitemp_DS9097 -h

# 初始化 .digitemprc 并扫描总线（需要真实串口适配器）
digitemp_DS9097 -i -s /dev/ttyS0

# 读取总线上所有传感器温度
digitemp_DS9097 -a
```

## 参考

- [源码仓库](https://github.com/bcl/digitemp)
- [DigiTemp 官方文档](https://github.com/bcl/digitemp/blob/master/README)
