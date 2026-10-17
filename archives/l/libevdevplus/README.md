# libevdevplus

libevdevplus 是一个面向 Linux evdev（输入子系统）的易用 C++ 封装库：在
`/dev/input/eventX` 与 Linux UAPI（`linux/uinput.h` / `linux/input.h`）之上，
用少量 C++ 类隐藏 `ioctl`/`read` 的样板代码，并提供键盘码映射表。

- 官方仓库：https://github.com/YukiWorkshop/libevdevPlus
- 许可证：MIT
- 版本：0.1.1（tag `v0.1.1`）
- 上游下载源：`https://github.com/YukiWorkshop/libevdevPlus/archive/refs/tags/v0.1.1.tar.gz`
  （sha256 `c941b6b45f784c1e6c6f316f59256fabd604ac392db405cf7fd99de2686aaab0`）
- 归档目录：`archives/l/libevdevplus/0.1.1/`（conanfile.py + conandata.yml + manifest.yaml
  + notes.md + test_package/）

## 功能概述

| 类型 | 说明 |
|------|------|
| `evdevPlus::EventDevice` | 事件设备对象：`Open()`/`Close()`/`Grab()`/`Ungrab()`/`Read()`，`IsValidDevice()` 用 `EVIOCGVERSION` 判定 fd 是否为事件设备 |
| `evdevPlus::EventDeviceID` | 设备 ID（BusType / Vendor / Product / Version），底层 `struct input_id` |
| `evdevPlus::InputEvent` | 单条输入事件（Type / Code / Value + 时间戳），底层 `struct input_event` |
| `evdevPlus::Table_*` | 键名→键码映射表：`Table_ModifierKeys`、`Table_FunctionKeys`、`Table_LowerKeys`、`Table_UpperKeys`、`Table_KeyCodes` |

公开头文件安装在 `include/evdevPlus/`（`evdevPlus.hpp`、`InputEvent.hpp`、
`CommonIncludes.hpp`），库文件为 `libevdevPlus.{a,so*}`，另装 `evdevPlus.pc`。

## OHOS 适配

**无补丁、无平台宏、无外部依赖。**

- 源码只依赖 C++ 标准库与 POSIX / Linux UAPI 头；其中唯一的"内核头"是
  `<linux/uinput.h>`（`CommonIncludes.hpp`），**OHOS SDK sysroot 直接提供**：
  `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/linux/uinput.h`
  同目录另有 `input.h` / `input-event-codes.h`。因此不需要像 Meson 系上游那样
  按 `host_machine.system()` 建 `include/linux/harmonyos/` 软链（libevdev 的先例）。
- 上游 `CMakeLists.txt` 首行为 `cmake_minimum_required(VERSION 3.0)`；CMake 4.x
  （本机与 CI 均为 4.x）已移除对 `< 3.5` 的兼容，configure 直接 hard error
  （`Compatibility with CMake < 3.5 has been removed`）。该检查早于
  `conan_toolchain.cmake` 加载，故 `tc.variables`/`tc.cache_variables` 均不可达，
  配方改用命令行缓存变量 `cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})`
  （coordgen 先例），**不改上游 CMakeLists**。
- 上游**无条件**同时构建并安装 `evdevPlus`(SHARED) 与 `evdevPlus_Static`(STATIC)
  两个目标，且不响应 Conan 惯用的 `BUILD_SHARED_LIBS`；本配方不设该变量
  （避免"设了但无效"的假开关），而是在 `package()` 中按 `options.shared` 只保留
  所选变体，防止同一包内 `.so`/`.a` 并存导致下游链接歧义。
- 运行期依赖：仅 libc / libstdc++（上游 `CPACK_DEBIAN_PACKAGE_DEPENDS` 为
  `libc6 (>= 2.14), libstdc++6 (>= 5.2)`）；`cpp_info.libs = ["evdevPlus"]`。
- 系统同名库检查（R26/G3）：设备 `/lib`、`/lib64` 下存在 `libevdev.z.so`（属于
  另一个包 libevdev），**不存在** `libevdevPlus`，故不触发系统同名库静态约束。

## 已知限制

- 上游唯一的测试性文件 `test.cpp` 是**手工演示程序**（`Usage: <event device>`，
  链接后进入 `while(true)` 读取真实事件设备），上游既未 `enable_testing()` 注册，
  也不安装它；构建机无法读 `/dev/input`（权限拒绝），故其不可自动化运行。
  上游自动化测试数 N = 0（清点证据见 `0.1.1/test_package/MANIFEST.yml` 与
  `0.1.1/reports/test-report.md`），功能验证由 `test_package` 消费者测试承担。
- 上游 `.pc.in` 里的 `Version:` 仍写死 `0.1.0`（上游文件未随 0.1.1 更新）；
  本仓库不改上游该字段，安装出的 `evdevPlus.pc` 因此自报 0.1.0。

## 依赖关系

- 编译依赖：CMake、C++11 编译器（OHOS SDK clang 15）；无第三方库。
- 运行依赖：libc、libstdc++。

## 参考资料

- 上游仓库：https://github.com/YukiWorkshop/libevdevPlus
- AUR `libevdevplus`：https://aur.archlinux.org/packages/libevdevplus
- 同族包（内核 evdev，C 库）：`archives/l/libevdev/1.13.7/`
