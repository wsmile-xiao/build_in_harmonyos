# NXP i.MX USB Loader

NXP i.MX USB Loader provides command-line tools for downloading and booting images on NXP i.MX devices over USB or UART.

## HarmonyOS PC notes

The Conan package builds the upstream `imx_usb` and `imx_uart` programs for HarmonyOS AArch64. It depends on `libusb/1.0.27`; the package places executables in `bin/` and device configuration files in `etc/imx-loader.d/`.

The upstream simulator tests run without a connected board. Real USB download and UART communication require a compatible i.MX device and were not part of this package test.

## Basic checks

```sh
imx_usb --help
imx_usb -V
imx_uart --help
```

## Source

- [Upstream repository](https://github.com/boundarydevices/imx_usb_loader)
