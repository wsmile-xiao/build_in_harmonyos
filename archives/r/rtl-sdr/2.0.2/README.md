# rtl-sdr

**RTL2832U 电视棒的软件无线电（SDR）库与工具集**，上游 Osmocom 项目：
<https://osmocom.org/projects/rtl-sdr/wiki>，代码 <https://github.com/osmocom/rtl-sdr>，
许可证 **GPL-2.0-or-later**。

```c
#include <rtl-sdr.h>

uint32_t n = rtlsdr_get_device_count();          /* 找电视棒 */
rtlsdr_dev_t *dev;
rtlsdr_open(&dev, 0);                            /* 打开 0 号设备 */
rtlsdr_set_center_freq(dev, 100000000);          /* 调谐到 100 MHz */
rtlsdr_read_async(dev, cb, ctx, 0, 0);           /* 拉 IQ 采样 */
```

命令行：`rtl_sdr`（录制）、`rtl_fm`（解调）、`rtl_tcp`（网络 SDR）、`rtl_test`
（自检）、`rtl_eeprom`、`rtl_adsb`、`rtl_power`、`rtl_biast`。

## OHOS（鸿蒙 PC / aarch64）适配状态

| 版本 | 状态 | 依赖 | 交付 |
|------|------|------|------|
| 2.0.2 | 已适配（消费者用例 14/14，CLI 冒烟 8/8，自检 23/23） | `libusb/1.0.27` | `librtlsdr.so` + `rtl-sdr.h` + `librtlsdr.pc` + 8 个 CLI + COPYING |

- **上游没有任何测试套件**（无 `enable_testing()`/`add_test`；`rtl_test` 是需要真实
  电视棒的硬件自检程序）——已如实声明。真跑的证据是 `build()` 内的 8 个 CLI 启动
  冒烟，以及 `test_package/test_rtlsdr.c` 的消费者用例：用 **ELF 符号介入**伪造一台
  `0x0bda:0x2838` 电视棒，跑通设备枚举 / 机型表匹配 / USB 字符串读取 / 序列号反查 /
  越界错误路径整条链路。
- 注意上游版本号 quirk：tag 是 v2.0.2，但根 `CMakeLists.txt` 里 patch 版本仍是 1，
  产物自报 2.0.1（`.pc` 的 `Version:` 也是 2.0.1）。
- **唯一的源码补丁** `patches/0001-ohos-portable-demod-thread-exit.patch`：OHOS 的
  musl libc 没有 `pthread_cancel()`，`rtl_adsb` 的退出路径改用它线程自带的 `do_exit`
  标志 + 条件变量唤醒后再 `join`（语义等价，musl/glibc 通用）；库本体不动。

## 使用（Conan 2）

```ini
[requires]
rtl-sdr/2.0.2
```

CMake：

```cmake
find_package(rtlsdr CONFIG REQUIRED)              # conan CMakeDeps 生成
target_link_libraries(app PRIVATE rtlsdr::rtlsdr) # 包名带 '-'，目标名已显式改好
```

pkg-config：包内 `lib/pkgconfig/librtlsdr.pc` 是**可重定位**的
（`prefix=${pcfiledir}/../..`），在任意安装前缀下 `pkg-config --cflags --libs
librtlsdr` 都指向包内的 `include/` 与 `lib/`。

## 适配要点

详见 `2.0.2/notes.md`：pkg-config 依赖发现（上游 `pkg_check_modules` 失败即 FATAL）、
OHOS 未知平台下自补 `-Wl,-soname,` + `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`、
剔除不可重定位的上游 CMake export 与 udev 规则、`.pc` 前缀重写、以及测试证据。
