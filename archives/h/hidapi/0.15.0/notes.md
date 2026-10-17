# hidapi 0.15.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-06
- 编译器: clang/clang++ (15.0.4)
- 状态: built (conan-verify passed, W3 本地 CI 通过)

## 编译步骤

使用 CMake 构建系统（libusb 后端，与 0.14.0 已验证方案一致），关键参数：
- `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` — CMake 4.x 兼容性（必须用 cache_variables）
- `-DHIDAPI_NO_ICONV=ON` — 禁用 Iconv (OHOS 不可用)
- `-DCMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` + `-DCMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,` — OHOS 未知平台下产出可重定位 ELF SONAME（E330）
- CMakeDeps 生成器用于解析 libusb 依赖

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载超时 | worker 网络无法直连 github.com | gh-proxy 镜像下载 tarball（conandata 只写官方 URL，CI 自动加镜像 fallback） |
| 2 | CMake 版本兼容性错误 | hidapi CMakeLists.txt 要求 cmake 3.1.3，系统 cmake 4.1.2 要求最低 3.5 | 设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（必须用 cache_variables 而非 variables） |
| 3 | Iconv 未找到 | OHOS 平台无 Iconv 库 | `-DHIDAPI_NO_ICONV=ON` 禁用 Iconv |
| 4 | libusb 依赖未找到 | hidapi CMakeLists.txt 用 TARGET usb-1.0 检测，Conan CMakeDeps 生成 libusb-1.0::libusb-1.0 | build() 中 replace_in_file 给 libusb/CMakeLists.txt 添加 find_package + conan target 检测 |
| 5 | L5 门禁: libhidapi-libusb.so 缺少 DT_SONAME + IMPORTED_NO_SONAME TRUE | OHOS 平台 CMake 未知平台（HarmonyOS）未定义 CMAKE_SHARED_LIBRARY_SONAME_C_FLAG，SOVERSION 未生效 | 显式设置 CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON + CMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,（E330 方案），产物带可重定位 SONAME |
| 6 | W3 junk_check full 模式误拦 HEAD 基线文件 archives/u/util-linux-login/2.42.2/.ci-trigger | 该 tracked 空文件由 util-linux-login 2.42.2 知识库扩展 PR 引入、未登记 JC5_ALLOWED；本地 full 模式整仓扫描命中 | 以 CI 同构 prdiff 模式复验（JUNK_PR_DIFF），基线文件不动、不 add、与 HEAD 一致恢复 |
| 7 | /tmp 写入失败（curl error 23） | /tmp 只读（E002） | 使用 $HOME/tmp |

## 源码修改

无补丁文件，build() 方法中使用 replace_in_file 运行时修改 libusb/CMakeLists.txt：
- 添加 `find_package(libusb-1.0 QUIET)` 和 Conan CMakeDeps target 检测

## 依赖版本

- libusb/1.0.27 (conan remote ohpcd，已发布)

## 验证结果

- conan-verify 8 道门禁全过（G0-G4 + L2/L4/L5）
- W3 本地 CI 模拟（setup.sh + build_and_test.sh）通过：conan create + test_package 1/1 通过
- L5 SONAME 门禁：libhidapi-libusb.so 带 SONAME=libhidapi-libusb.so，无 IMPORTED_NO_SONAME
- test_package 实际调用 hid_version_str/hid_init/hid_enumerate/hid_exit（容忍无头系统 hid_init 失败）

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake + libusb 后端配方（含 SONAME 修复） |
| conandata.yml | 官方源 URL + sha256 |
| test_package/ | 消费者验证测试 |
| manifest.yaml | 版本级元数据 |

---

**编译结束**: 2026-09-06
**最终状态**: built
