# teensy_loader_cli 2.3 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile 项目，无 autotools）
- 编译日期: 2026-05-21
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: built

## 编译步骤

1. `./configure --prefix=$DEFAULT_PREFIX` — dummy configure 脚本（纯 Makefile 项目）
2. `make -j1 PREFIX=$DEFAULT_PREFIX` — 编译，使用静态链接 libusb-1.0
3. `make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX` — staging 安装
4. `teensy_loader_cli --list-mcus` — R7 安全弹窗验证，PASS
5. `make check` — 无 check target，跳过
6. `ohc-run.py package teensy_loader_cli 2.3` — 打包
7. `make install PREFIX=$DEFAULT_PREFIX` — 本地部署
8. `ohc-run.py finish teensy_loader_cli 2.3 built` — 收尾

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码使用旧版 libusb-0.1 API (`usb.h`, `-lusb`) | 原始代码针对 Linux 使用 libusb-0.1 (deprecated) | 移植到 libusb 1.0 API: `#include <libusb.h>`, 使用 `libusb_*` 函数族, 需要安装 libusb 1.0.27 预编译包 |
| 2 | LD_LIBRARY_PATH 在 OHOS 上不生效 | HMDFS 动态链接器限制 | 静态链接 libusb (`-l:libusb-1.0.a`) |
| 3 | Makefile 无 install target | 原始项目只有 clean target | 添加 install target 到 Makefile |
| 4 | 无 configure 脚本 | 纯 Makefile 项目无 autotools | 创建 dummy configure 脚本 (E105 模式) |
| 5 | libusb 安装在 libusb-package 子目录 | cmd-pkgs 安装脚本将依赖包放在独立子目录 | Makefile 中 LIBUSB_CFLAGS/LIBUSB_LDFLAGS 使用 $(PREFIX)/libusb-package/ |

## 源码修改

### teensy_loader_cli.c
- USE_LIBUSB 区段 (行 211-359) 从 libusb-0.1 API 移植到 libusb 1.0 API
  - `#include <usb.h>` → `#include <libusb.h>`（配合 -I 搜索路径）
  - `usb_dev_handle` → `libusb_device_handle`
  - `usb_init/usb_find_busses/usb_find_devices` → `libusb_init + libusb_get_device_list`
  - `usb_open/usb_close` → `libusb_open/libusb_close`
  - `usb_control_msg` → `libusb_control_transfer`
  - `usb_claim_interface/usb_release_interface` → `libusb_claim_interface/libusb_release_interface`
  - `usb_get_driver_np/usb_detach_kernel_driver_np` → `libusb_kernel_driver_active/libusb_detach_kernel_driver`
  - `usb_strerror()` → `libusb_strerror(LIBUSB_ERROR_IO)`
  - 添加 `static libusb_context *usb_context = NULL` 用于全局 libusb context

### Makefile
- CC 默认改为 clang
- CFLAGS 增加 -fPIC
- 添加 LIBUSB_CFLAGS/LIBUSB_LDFLAGS 变量，指向 libusb-package 子目录
- 链接改为 `-l:libusb-1.0.a`（静态链接）
- 添加 `-include config.mk` 支持 configure 生成的 PREFIX
- 添加 `install` target

### configure (新增)
- dummy configure 脚本，仅处理 --prefix 参数
- 生成 config.mk 供 Makefile 读取

## 依赖版本

- libusb 1.0.27（预编译包，静态链接）
- clang 15.0.4

## 验证结果

```bash
$ teensy_loader_cli --list-mcus
Supported MCUs are:
 - at90usb162, atmega32u4, at90usb646, at90usb1286
 - mkl26z64, mk20dx128, mk20dx256, mk66fx1m0, mk64fx512, imxrt1062
 - TEENSY2, TEENSY2PP, TEENSYLC, TEENSY30, TEENSY31
 - TEENSY32, TEENSY35, TEENSY36, TEENSY40, TEENSY41, TEENSY_MICROMOD
```

## 注意事项

- libusb 必须静态链接（OHOS LD_LIBRARY_PATH 不可靠）
- libusb 预编译包安装在 `~/usr/local/libusb-package/` 子目录，需要手动设置 include/lib 路径
- 项目虽标注为 autotools，但实际是纯 Makefile，需要 dummy configure + install target 补丁（E105 模式）
---

**编译结束**: 2026-05-21 20:44
**最终状态**: built
