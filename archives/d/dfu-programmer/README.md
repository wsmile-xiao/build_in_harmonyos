# dfu-programmer

**分类**: 开发工具 / USB 设备  
**版本**: 1.1.0  
**状态**: published  
**编译日期**: 2026-06-09

dfu-programmer 是一个用于通过 USB DFU 协议对 Atmel AVR 和 XMEGA 微控制器进行编程的开源工具。

构建系统: Autotools  
编译依赖: libusb 1.0.27

编译要点:
- 设置 TMPDIR=/data/storage/el2/base/cache
- 运行 bootstrap.sh 生成 configure
- 设置 PKG_CONFIG_PATH/LDFLAGS/CPPFLAGS

GitHub: https://github.com/dfu-programmer/dfu-programmer
