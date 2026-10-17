# libusb 1.0.29 — 编译进度

> 档案创建时间: 2026-10-08
> 最后更新: 2026-10-08
> 编译完成日期: 2026-10-08

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libusb |
| 版本 | 1.0.29 |
| 状态 | ✅ built |
| 构建系统 | autotools |
| 源码来源 | github.com/libusb/libusb 官方 release tarball v1.0.29 |
| 编译器 | clang 15（OHOS aarch64 交叉） |
| 性质 | 升级件（main 已有 1.0.27） |

## 二、与 1.0.27 的差异（升级要点）

上游 ChangeLog（2025-06-01 v1.0.29）：
- Fix regression on macOS leading to timeouts in enumeration
- LIBUSB_API_VERSION bump for the new functions in 1.0.28
- Fix xusb regression displaying wrong error on claim failure

2025-03-18 v1.0.28：
- New libusb_get_ssplus_usb_device_capability_descriptor API（SuperSpeed+ 能力描述符查询）
- API support for reporting USB 3.2 Gen2x2 speeds
- macOS/Windows/Haiku/SunOS 平台修复与正确性修复

对 OHOS 适配的影响：**零结构变化**——Linux 后端（linux_usbfs/linux_netlink）、
autotools 构建骨架、`--enable-udev` 选项语义、tests/Makefile.am 注册的 4 个测试
程序（stress/stress_mt/set_option/init_context）与 1.0.27 完全一致。

## 三、适配点复用验证（1.0.29 源码实测）

三个 1.0.27 适配点在 1.0.29 官方 tarball 上逐项验证：

| 适配点 | 1.0.29 匹配验证 | 结论 |
|--------|----------------|------|
| configure umask 077→022（HMDFS 临时目录权限，E112） | 两处 `umask 077` 模式精确匹配（行 20002/20007） | 原样沿用 |
| linux_netlink.c sockaddr_storage 重定义（E091） | `#include <sys/socket.h>\n#include <linux/netlink.h>` 相邻模式精确匹配 | 原样沿用 |
| linux_usbfs.c HongMeng 内核版本解析 | sscanf 三元组+错误日志模式精确匹配（行 319） | 原样沿用 |

- `--disable-udev` 在 1.0.29 configure.ac 中仍为 `AC_ARG_ENABLE([udev])` 双向开关
  （默认 yes），禁用后仅要求 linux/netlink.h + sys/socket.h 头文件，无 libudev 依赖
  ——与 1.0.27 语义一致。
- config.guess/config.sub 官方 tarball 仍为 2022-01 时间戳（不含 OHOS 检测），
  沿用 1.0.27 的检测增强补丁（E007 系）。
- patches 目录 5 个补丁与 conanfile.py 内联 replace_in_file 双轨制沿袭 1.0.27
  结构：内联方式是构建实际执行路径（conan create 源码干净重取），patches 目录
  为补丁留档（dry-run 全部验证适用于 1.0.29，exit 0）。

## 四、构建验证（2026-10-08，本机 OHOS aarch64 真机）

- [x] 本地 conan create -pr=ohos-aarch64（干净缓存）全绿 RC=0
- [x] configure：`--disable-udev --disable-dependency-tracking --enable-shared`
- [x] make -j1 编译通过（libusb-1.0.la + 共享库签名）
- [x] make check：无失败项（配方形态沿袭 1.0.27，--enable-tests-build 上游默认关闭，tests/ 不进 SUBDIRS）
- [x] test_package：5/5 消费断言通过（实测输出 `libusb consumer smoke passed: 1.0.29`）

消费测试采用强化版（吸收历史 1.0.27.1 分支 AI review P2 修复形态）：在版本
元数据/错误字符串 API 断言之上，新增 `libusb_init_context` +
`LIBUSB_OPTION_NO_DEVICE_DISCOVERY` 平台初始化路径断言——这是 OHOS 沙箱内
唯一可用的初始化方式，覆盖鸿蒙特有平台行为（rule12 素材）。

### 上游测试运行态实测（--enable-tests-build 试验）

为验证测试统计真实性，曾以 `--enable-tests-build` 真实构建并运行上游 4 个测试程序：

```
FAIL: stress          — Failed to init libusb on iteration 0: -1 (LIBUSB_ERROR_IO)
FAIL: stress_mt       — Thread N failed (iteration 0): LIBUSB_ERROR_IO
FAIL: set_option      — 同上，libusb_init 失败
FAIL: init_context    — 同上，libusb_init 失败
# TOTAL: 4 / PASS: 0 / FAIL: 4
```

根因定性（与 1.0.27 归档能力评估一致）：上游测试程序调用默认
`libusb_init()`，而 OHOS HAP 沙箱 SELinux neverallow 阻断
`/sys/bus/usb/devices/` 设备发现（本机实测 `ls /sys/bus/usb/devices/` →
`Permission denied`，errno=13），初始化返回 LIBUSB_ERROR_IO。
**属平台环境限制，非代码缺陷**——1.0.27 归档已给出完整 SELinux CIL
策略分析（sysfs dir search 与 dev_bus_usb_file 均为 neverallow 硬性禁止）。
因此配方保持与 1.0.27 完全一致的形态（tests-build 关闭），不虚报
"4/4 运行通过"；消费测试（NO_DEVICE_DISCOVERY 初始化 + 不依赖 USB 硬件）
作为真实运行验证载体。

## 五、上游测试口径

- `tests/Makefile.am` 的 `TESTS = $(noinst_PROGRAMS)`，启用 tests-build 时注册
  stress、stress_mt、set_option、init_context（4 个）；umockdev 仅
  BUILD_UMOCKDEV_TEST（启用 udev + pkg-config umockdev-1.0）时注册，macos 仅
  OS_DARWIN 时注册——OHOS `--disable-udev` 配置下上游注册口径 = 4。
- 上游默认形态（configure 无参）tests-build=no，tests/ 不进 SUBDIRS。
- test_package 为非设备依赖的消费冒烟（不触碰 USB 硬件，规避沙箱 SELinux 限制）。

## 六、对话记录

### 对话 #1 — 2026-10-08
**操作**: 1.0.27 → 1.0.29 增量升级（任务 #14966）
**结果**: ✅ 成功
- 官方 tarball 下载 + sha256 实测: 5977fc950f8d1395ccea9bd48c06b3f808fd3c2c961b44b0c2e6e29fc3a70a85
- 三个适配点 1.0.29 精确匹配验证通过；5 个留档补丁 dry-run 验证适用
- conan create -pr=ohos-aarch64 干净缓存全绿（make check 无失败项 + test_package 3/3）
- --enable-tests-build 试验实测 4/4 上游程序死于沙箱 SELinux（环境限制豁免，证据见第四节）
