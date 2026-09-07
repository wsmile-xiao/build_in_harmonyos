# openhmd 0.3.0 适配笔记

## 编译环境
- 构建系统: cmake（上游三构建系统 cmake/autotools/meson 中的主路径；
  autotools 需 automake bootstrap（环境缺 automake），meson 未安装——
  CMake 是唯一可用且上游默认的路径）
- 编译日期: 2026-09-05
- 编译器: clang/clang++（OHOS SDK，--target=aarch64-linux-ohos 由 conan toolchain 注入）
- 状态: published

## 编译步骤

1. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... -pr:b=...`（配方内自动完成）：
   - `source()`: 下载 GitHub tag 0.3.0 tarball（sha256 ec5c97ab...）
   - `generate()`: CMakeDeps + CMakeToolchain + 写 ohmd_hidapi_cache.cmake（见下）
   - `build()`: `cmake -C generators/ohmd_hidapi_cache.cmake <src> && cmake --build .`
   - `package()`: `cmake --install`（产出 lib/libopenhmd.a + include/openhmd.h + lib/pkgconfig/openhmd.pc）
   - `test_package/`: 上游 unittests 完整移植（见验证结果）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x 报 "Compatibility with CMake < 3.5 has been removed" | 上游 2019 年代码 `cmake_minimum_required(VERSION 3.1)`，CI 的 CMake 4.1.2 已移除 <3.5 兼容 | 在 `-C` 初始 cache 文件里 `set(CMAKE_POLICY_VERSION_MINIMUM "3.5" CACHE STRING ...)`（CMake 官方兼容开关），**零源码补丁** |
| 2 | 驱动源码 `#include <hidapi.h>` 找不到（fatal error: 'hidapi.h' file not found） | conan toolchain 开启 `CMAKE_FIND_PACKAGE_PREFER_CONFIG ON`，上游 `find_package(HIDAPI)`（module 模式，配 cmake/FindHIDAPI.cmake）被 CMakeDeps 生成的 hidapi-config.cmake（config 模式）抢占；config 只定义 imported target，不设上游 CMakeLists 消费的 `HIDAPI_INCLUDE_DIRS`/`HIDAPI_LIBRARIES` 变量 → include_directories 为空 | 初始 cache 文件预置全部四个变量（单数 HIDAPI_LIBRARY/HIDAPI_INCLUDE_DIR = Find 模块结果变量；复数 HIDAPI_LIBRARIES/HIDAPI_INCLUDE_DIRS = CMakeLists 消费变量），两条查找路径都通 |
| 3 | 上游单元测试不在 CMake 构建里 | 上游 tests/unittests 只有 Makefile.am（autotools）与 meson.build 定义，CMakeLists.txt 不含 tests/ | test_package 完整移植上游 11 个测试（vec3f×4/quatf×5/highlevel×2）+ 公共 API 扩展×2，测试数据与断言逐项对齐上游源码 |
| 4 | OHMD_VERSION 不是 ohmd_gets 的合法枚举 | 上游 0.3.0 的 ohmd_string_description 只有 GLSL 着色器源码枚举（VERSION 字符串 API 是后续版本加的） | 版本验证改用 ohmd_get_version()（int 返回 0,3,0），字符串 API 冒烟用 OHMD_GLSL_DISTORTION_VERT_SRC |
| 5 | 自加的 quat[3]==1.0f 断言失败 | 误解 API 语义：ohmd_device_getf(OHMD_ROTATION_QUAT) 返回的是 device->rotation（融合状态，初始全 0，由更新线程填充），不是驱动 getf 的原始值 | 改为确定性属性断言：dummy HMD 屏幕分辨率 1280x800（ohmd_device_geti 直读 properties）+ 控制器状态 (0.1, 1.0)（dummy getf OHMD_CONTROLS_STATE） |

## 源码修改

**无补丁**（conandata.yml `patches: {}`）。上游源码零修改：
- CMake 兼容性经 CMAKE_POLICY_VERSION_MINIMUM 传参解决
- HIDAPI 消费经 cache 变量注入解决

## 依赖版本

- hidapi/0.14.0（制品仓，libusb 后端 → libhidapi-libusb.so + libusb/1.0.27）
- 上游 configure.ac 声明 hidapi >= 0.0.5，0.14.0 满足

## 平台适配完整性（R40 深度检查）

openhmd 是用户态 VR 驱动库（hidapi 消费者），适配完整性逐项核验：

1. **编译**：全部 6 个 HID 驱动（Oculus Rift/Deepoon/WMR/HTC Vive/NOLO/3Glasses）
   + External + dummy 编译通过——驱动逻辑非 stub
2. **运行时设备枚举**：本机（OHOS PC）实测 `ohmd_ctx_probe` 返回 4 个设备
   （External Device + HMD Null Device + Left/Right Controller Null Device）——
   设备枚举链路（driver 注册 → get_device_list → list 聚合）真实工作
3. **HID 接口平台差异（重要）**：OHOS 内核**存在** /dev/hidraw0/1/2 与
   /dev/bus/usb 节点（本机 shell 用户无权限访问，但节点存在）；本次用的
   hidapi/0.14.0 是 **libusb 后端**（走 /dev/bus/usb 的 libusb 枚举），非
   hidraw 后端——OHOS PC 上 libusb 枚举路径已由 libusb/1.0.27 包适配覆盖
4. **真实 HMD 硬件**：OHOS PC 无 VR 头显连接，真实驱动的 I/O 无法端到端
   验证（所有平台共同的限制——dummy 驱动即为此设计）；测试覆盖到设备
   枚举 + 打开/关闭 + 属性读取 + 数学库全量断言

## 验证结果

```bash
# R40 实测：本机 OHOS PC 运行上游示例（examples/simple/simple，设备枚举真实输出）
$ ./simple
OpenHMD version: 0.3.0
num devices: 4

device 0
  vendor:  OpenHMD
  product: External Device
  path:    (none)
  class:   HMD
  flags:   06
    null device:         no
    rotational tracking: yes
    positional tracking: yes
device 1
  product: HMD Null Device  (class: HMD, flags: 05, null device: yes)
device 2
  product: Left Controller Null Device
device 3
  product: Right Controller Null Device

# conan create 测试输出（13/13）
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
...
vec3f tests
   test_ovec3f_normalize_me                          ok
   test_ovec3f_get_length                            ok
   test_ovec3f_get_angle                             ok
   test_ovec3f_get_dot                               ok

quatf tests
   test_oquatf_init_axis                             ok
   test_oquatf_get_rotated                           ok
   test_oquatf_get_dot                               ok
   test_oquatf_inverse                               ok
   test_oquatf_diff                                  ok

high level tests
   test_highlevel_open_close_device                  ok
   test_highlevel_open_close_many_devices            ok

public api tests
   test_public_api_version                           ok
   test_public_api_probe_enumeration                 ok

all a-ok
100% tests passed, 0 tests failed out of 1
```

上游测试对比：上游 unittests 共 11 个 Test()（vec3f 4 + quatf 5 + highlevel 2），
本包全部移植并通过，另补 2 个公共 API 测试，共 13 项全绿。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（CMake 构建 + hidapi 依赖 + cache 变量注入） |
| conandata.yml | 源码 URL + sha256（零补丁） |
| test_package/ | 上游 unittests 完整移植 + 公共 API 测试 |
| manifest.yaml | 本元数据 |
| notes.md | 本笔记 |

## 注意事项

- 本包是 hidapi 的**消费者**：制品仓的 hidapi/0.14.0 为 libusb 后端。若下游
  需要 hidraw 后端（内核 /dev/hidraw 直连），需另行适配 hidapi 的 hidraw 变体
- 上游 0.3.0 的 ohmd_gets 不支持版本字符串（OHMD_VERSION 枚举为后续版本引入）
- CMAKE_POLICY_VERSION_MINIMUM=3.5 是 CMake 官方对旧项目的兼容开关，上游若
  更新 cmake_minimum_required 后可移除
---

**编译结束**: 2026-09-05 14:53
**最终状态**: built
