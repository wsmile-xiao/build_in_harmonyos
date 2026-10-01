# isight-firmware-tools — Apple 内置 iSight 固件工具

Apple 内置 iSight 摄像头需要固件；固件只能从 Mac OS X 的
`AppleUSBVideoSupport.kext` 驱动文件中提取。本包提供三个程序：

- **`ift-extract`**：从驱动文件中定位并提取固件。
- **`ift-export`**：把提取出的固件转换成 Intel HEX 格式。
- **`ift-load`**：通过 USB（libusb）把固件上传到摄像头（通常由 udev 触发）。

## 用法

```sh
ift-extract -a AppleUSBVideoSupport -d . -f isight.fw   # 提取
ift-export  -i isight.fw -o isight.ihx                  # 转 Intel HEX
ift-load    -f isight.fw                                # 上传到设备
```

## OHOS 适配要点

- 上游为 autotools 工程（自带 `configure`），但其 2012 年的 `config.sub` 不识别
  aarch64/HarmonyOS，且 `configure` 期需要 intltool/gettext。本配方**绕过整个引导链**，
  直接用 OHOS clang 编译三个程序并提供最小 `config.h`（与 sxid/libblocksruntime 同法）。
- 依赖：glib-2.0、libgcrypt、libusb-compat（`usb.h`），以及 `gettext-tiny`——
  glib 2.84 的 `gi18n.h` 无条件把 `_()` 展开为 `gettext()`，而 OHOS sysroot 的
  `libintl.h` 是无 `gettext` 声明的空壳，需用 gettext-tiny 的 `libintl.h` 提供真声明。
- 上游无测试套件（`tests/Makefile.am` 只遍历未随包分发的 `AppleUSBVideoSupport*` 驱动文件）。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/ift-extract` | 固件提取 |
| `bin/ift-export` | 固件 → Intel HEX |
| `bin/ift-load` | USB 固件上传 |
| `share/man/man1/*.1` | 手册页 |

## 参考资料

- 上游：<https://launchpad.net/isight-firmware-tools/>
- 许可证：GPL-2.0-or-later
