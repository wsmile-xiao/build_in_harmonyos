# libusbgx

USB Gadget 配置库的扩展版本，用于配置和管理 USB Gadget 设备。

## 功能
- USB Gadget 设备配置
- 支持多种 USB 功能（ACM, ECM, HID, MIDI, etc）

## 依赖
- libconfig >= 1.4

## 编译
```bash
autoreconf -fi
./configure --prefix=$HOME/usr/local
make -j2
make install
```

## 版本
- 0.3.0: 2026-06-12 编译通过
