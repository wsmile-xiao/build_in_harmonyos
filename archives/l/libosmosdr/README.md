# libosmosdr

**描述**: libosmosdr 是 OsmoSDR 用户态驱动库，用于访问基于 OsmoSDR、E4000、FC0012、FC0013 芯片的 USB DVB-T 接收器。

**主页**: https://osmocom.org/projects/sdr/wiki/Libosmosdr

**许可证**: GPL-2.0-or-later

**分类**: library

**上游仓库**: https://osmocom.org/projects/sdr/wiki/Libosmosdr（源码由 Debian pool 归档，见 conandata.yml）

## 版本

### 0.1.8.effcaa7 (2026-09-16)
- **状态**: published
- **构建系统**: cmake
- **依赖**: libusb/1.0.27
- **源码**: Debian 官方归档 `libosmosdr_0.1.8.effcaa7.orig.tar.xz`
- **补丁**: 1 个（`patches/0001-src-libosmosdr.c.patch`，portability：libusb 返回值检查，修复无 USB 环境下的 Signal 11）
- **测试**: 4 个用例 / 13 条断言，全部通过（详见 `0.1.8.effcaa7/reports/test-report.md`）

## 基本信息

| 项目 | 值 |
|------|-----|
| 版本 | 0.1.8.effcaa7 |
| 构建系统 | cmake |
| 许可证 | GPL-2.0-or-later |
| 架构 | aarch64 (ARM64) |
| 动态依赖 | `libusb-1.0.so`（由 Conan 依赖链提供） |
| 命令行工具 | `osmo_sdr`（见 `commands.json`） |
| 编译日期 | 2026-09-16 |

## 说明

libosmosdr 提供 SDR 硬件的枚举与打开接口（`osmosdr_get_device_count()`、
`osmosdr_get_device_name()`、`osmosdr_open()`、`osmosdr_close()` 等），
底层通过 libusb 访问 USB 设备。

### 编译说明

上游 tarball **不包含 `configure` 脚本**，且其 `Makefile.am` 使用已废弃的
`AM_CONFIG_HEADER`，`autoreconf` 无法在现代 autotools 下重建。因此本归档
使用上游自带的 CMake 构建系统。

四处必须处理的平台差异（其中仅第 4 项需要补丁）：

1. **CMake 策略下限**：上游声明 `cmake_minimum_required(VERSION 2.6)`，
   宿主 CMake 4.x 拒绝 3.5 以下的策略下限并直接报错。通过
   `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 缓存变量解决，**无需补丁**。

2. **`.pc` 中残留构建机绝对路径**：上游 `libosmosdr.pc.in` 剥离构建期 `-I`
   绝对路径的逻辑被 `IF(CMAKE_CROSSCOMPILING)` 守卫，而鸿蒙 PC 是
   **原生构建（native build）**，该标志恒为假，守卫分支不执行，导致 Conan
   缓存的 `-I` 路径被写进制品。本归档在 `package()` 中清理该路径。
   （知识条目：草稿 E580）

3. **同名库变体**：上游同时安装 `osmosdr_shared` 与 `osmosdr_static`，
   安装后均为 `libosmosdr.{so,a}`。本配方按 `shared` 选项裁剪，避免
   `-losmosdr` 静默解析到未选中的变体。

4. **无 USB 环境崩溃（本版本唯一补丁）**：上游 `osmosdr_get_device_count()` /
   `osmosdr_get_device_name()` / `osmosdr_get_device_usb_strings()` /
   `osmosdr_open()` 不检查 `libusb_init()` 与 `libusb_get_device_list()` 的
   返回值。运行环境没有可用 USB 栈时（CI worker 无法访问 USB 设备节点）
   这两个调用失败且出参保持未初始化，随后解引用未初始化指针 →
   `Signal 11 (core dumped)` / `Error 139`。补丁
   `patches/0001-src-libosmosdr.c.patch` 将出参初始化为 `NULL`，失败时按
   "无设备"返回（设备数 `0` / 名字 `""` / 错误码），列表获取失败时先
   `libusb_exit(ctx)` 再返回；不含任何平台宏，对所有平台均有正向作用。
   （知识条目：草稿 E581）
   > 注意：同一二进制在**有** USB 的开发机上完全正常，本缺陷只在无 USB
   > 的运行环境暴露，属环境相关崩溃，故本机 W3 通过不能替代 CI 验证。

### 测试说明

上游**未附带任何测试**：源码树无 `tests/` 目录，`CMakeLists.txt` 无
`enable_testing()` / `add_test()` / `ctest` 调用，也无 `check` 目标。
本归档补充 4 个消费者测试用例（13 条断言），其中 TC-03、TC-04 为鸿蒙特有：

| 用例 | 内容 | 来源 |
|------|------|------|
| TC-01 | 设备枚举行为 | 适配新增 |
| TC-02 | 无硬件时的错误契约 | 适配新增 |
| TC-03 | OHOS 加载器下 `dlopen` 可加载性（⭐ 鸿蒙特有） | 适配新增 |
| TC-04 | `osmo_sdr` 命令行工具在 OHOS 上可执行（⭐ 鸿蒙特有） | 适配新增 |

本包**未登记** `ci/config/no_official_test.txt`：该白名单会整体跳过
L1a–L1d 检查，而本包有真实消费者测试，应当被实际验证而非豁免。

### 平台限制

- 设备枚举在**无 SDR 硬件的环境**下返回 0、设备名为空字符串，属预期安全行为。
- 实际 USB 硬件通信能力受平台 SELinux 策略约束，本归档未做真机硬件验证。
