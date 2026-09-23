# libcacard

CAC (Common Access Card) library that provides emulation of smart cards
to a virtual card reader running in a guest virtual machine. SPICE 项目组件，
曾为 QEMU 的一部分（QEMU 2.5 之前），实现 DoD CAC 标准。

## OHOS 适配

- **构建系统**：meson（与上游官方一致，不使用 autotools 分支）
- **依赖**：glib-2.0（>= 2.32）、nss（>= 3.12.8）；PC/SC 直通默认关闭，
  不依赖 pcsc-lite/libusb
- **签名**：meson install 重写 rpath 后必须用 binary-sign-tool 重签 ELF

## 参考

- 上游仓库：https://gitlab.freedesktop.org/spice/libcacard
- 源码包：https://www.spice-space.org/download/libcacard/
- API 文档：源码包内 docs/libcacard.txt
