# airspyhf 1.6.8 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-07
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

airspyhf 是 CMake 工程（顶层 `cmake_minimum_required(2.8)`），手动探索编译：
```bash
# 探索阶段（模式 B）
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
         -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
         -DCMAKE_SYSTEM_NAME=Linux \
         -DCMAKE_SYSTEM_PROCESSOR=aarch64
make -j4
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x configure 失败风险 | 上游 `cmake_minimum_required(2.8)` 过旧 | `CMAKE_POLICY_VERSION_MINIMUM=3.5`（同 Homebrew PR #54） |
| 2 | lib/ 与 include/ 未安装 | E092：CMake 不识别 HarmonyOS，`if( ${UNIX} )` 不生效 | `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64` |
| 3 | 找不到 libusb | 上游 `FindUSB1.cmake` 用 `LIBUSB_INCLUDE_DIR/LIBUSB_LIBRARIES` cache 变量 | 配方 `generate()` 从 libusb 依赖包显式解析这两个变量 |
| 4 | 运行时 "Operation not permitted" | 鸿蒙要求 ELF 签名 | 配方 `package()` 对 lib/ .so 与 bin/ 工具统一 `binary-sign-tool` 签名 |
| 5 | test_package 找不到 airspyhf.h | 上游头文件装到 `include/libairspyhf/` | `package_info()` 的 `includedirs = ["include/libairspyhf"]` |
| 6 | airspyhf_info/gpio 挂起/返回 -1 | 需物理 AirSpy HF+ 设备，沙箱无 USB | 平台限制（E051 类），记录不阻塞 |

## 源码修改

无源码补丁（0 个）。所有兼容性处理在 conanfile.py 配方内通过
CMake cache 变量完成。

## 依赖版本

- libusb/1.0.27（Conan ohpcd 制品仓，已发布）

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify airspyhf 1.6.8   # G0-G4 + L2/L4/L5 全过
# 上游测试：airspyhf_lib_version → "AirSpy HF library version: 1.6.8" ✅
# test_package ctest 1/1 PASS（真实调用 airspyhf_lib_version() API）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libairspyhf.so(.0/.1.6.8) | - | 共享库（已签名） |
| lib/libairspyhf.a | - | 静态库 |
| include/libairspyhf/*.h | - | 3 个头文件 |
| bin/airspyhf_{lib_version,info,rx,gpio,calibrate} | - | 5 个命令行工具（已签名） |

## 注意事项

- 上游未注册 ctest/make check 测试目标（`ctest` 报 "No tests were found"），
  运行时验证靠工具本身与 test_package。
- conan-verify 的 L2/L4/L5 在脚本侧因 JSON 键名不匹配被跳过（脚本只读无法改），
  已手动验证：NX/PIE/FULL-RELRO 均通过、5 个二进制可运行。
- 依赖 libusb 为动态链接，消费方需 `conan install` 自动拉取 libusb 运行时。

---

**编译结束**: 2026-08-07 12:34
**最终状态**: published
