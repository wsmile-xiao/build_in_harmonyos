# imx_uart_loader

NXP i.MX5/6/7/8 系列串口(UART)引导加载工具，为 OpenHarmony PC 打包。

| 项目 | 值 |
|---|---|
| 上游 | https://github.com/boundarydevices/imx_usb_loader |
| 版本 | `0_git20201102`（对应上游 commit `30b43d69`） |
| 源码 | https://github.com/boundarydevices/imx_usb_loader/archive/30b43d69770cd69e84c045dc9dcabb1f3e9d975a.tar.gz |
| SHA-256 | `4357907c9669874d3ccbf00395bf0b1733c26e6daea85d721f1c0cd897f4162c` |
| 构建系统 | GNU Make |
| 语言 | C |
| 许可证 | LGPL-2.1-only |
| 交付物 | `bin/imx_uart` |

## 为什么是这个名字

上游 `imx_usb_loader` 一个 Makefile 产出两个二进制：

- `imx_usb` —— USB（SDP）加载器，链接 `imx_sdp_simulation.o`，需要 libusb；
- `imx_uart` —— **串口**加载器，**不**链接模拟层，也**不**链接 libusb。

本任务名为 `imx_uart_loader`，因此只打包 UART 变体。这与 Alpine 的
`imx_loader` 源码包划分一致：`imx_uart_loader` 子包恰好只拥有
`/usr/bin/imx_uart`，而 `/usr/bin/imx_usb` 与 `/etc/imx-loader.d/` 属于另一个
`imx_usb_loader` 子包。

`0_git20201102` 取自 Alpine `imx_loader` 的 `pkgver`，其 APKBUILD 固定了
`_commit=30b43d69770cd69e84c045dc9dcabb1f3e9d975a`；本配方直接取该 commit 的
**上游 GitHub 源码包**，而非任何发行版重打包。

## 依赖

- `libusb/1.0.27` —— **仅为构建并运行上游测试所需的 `imx_usb`**。打包出来的
  `imx_uart` 本身不引用 libusb（只有 `imx_usb.c` 包含 `<libusb.h>`，且上游给
  `imx_uart` 的链接行不含 `$(USBLDFLAGS)`）。

## 上游测试

`tests/Makefile` 定义了 3 个用例，通过内建 SDP 模拟
（`imx_usb -v -S 0x15a2:0x0061 <image>`）与签入的 golden 输出逐字节比对：

1. `test.imx.test`
2. `test-dcd.imx.test`
3. `test-plugin.imx.test`

**覆盖说明**：该套件驱动的是 `imx_usb`，不是本配方打包的 `imx_uart`。
`imx_uart` 链接了 `imx_sdp.o`、`imx_loader_config.o`、`sdp.o`，这些翻译单元确实
被覆盖；但 `imx_uart.c` 自身的逻辑**不被任何上游测试覆盖**。详见 `notes.md`。
