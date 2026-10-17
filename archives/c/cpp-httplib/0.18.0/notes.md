# cpp-httplib 0.18.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-29
- 状态: built（R01 bootstrap + 首轮本地验证）
- 特殊说明: header-only 库，默认 HTTPLIB_COMPILE=OFF，仅安装 httplib.h

## 库简介

cpp-httplib 是一个 C++11 单头文件 HTTP/HTTPS 客户端/服务端库。
- 上游仓库: https://github.com/yhirose/cpp-httplib
- 许可证: MIT
- 类型: header-only（INTERFACE library）

## 官方来源核验（R01 bootstrap）

- 官方仓库: https://github.com/yhirose/cpp-httplib
- 正式 tag: v0.18.0
- tag commit: e64379c3d71ccf3f62e4e4853bfd1316901564b3
- 源码包: https://github.com/yhirose/cpp-httplib/archive/refs/tags/v0.18.0.tar.gz
- SHA-256: 6ed5894bbbc4a34a0f4c5e962672d0003d2ea099bbadacc66f6dee2b213ff394
- 头文件版本串: `#define CPPHTTPLIB_VERSION "0.18.0"`

## Conan 配方说明

### 配方结构
- `conanfile.py`: Conan 配方，使用 CMake 工具链，header-library
- `conandata.yml`: 官方源码 URL + SHA256
- `test_package/`: 消费者测试，验证 httplib.h 可包含并实例化 Server/Client

### 关键配置
- `package_type = "header-library"`：纯头文件库
- `package_id` 使用 `self.info.clear()`：所有 settings 组合产出相同包
- `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=str(self.settings.arch)`：规避 E092（CMake 不识别 OHOS）
- `HTTPLIB_INSTALL=ON` / `HTTPLIB_TEST=OFF` / `HTTPLIB_COMPILE=OFF`：仅安装头文件
- 禁用 `HTTPLIB_USE_*_IF_AVAILABLE`：header-only 模式避免 optional 依赖查找耦合
- 上游 `find_package(httplib)` → `httplib::httplib` 目标

### 平台适配
- R32: `self.settings.os in ("Linux", "OHOS")` 平台判断
- E092: 通过 CMakeToolchain 设置 CMAKE_SYSTEM_NAME=Linux 规避鸿蒙平台未知问题

## 依赖

header-only 模式无必需依赖；可选依赖 OpenSSL（HTTPS）、Zlib（压缩）、Brotli（压缩），
当前配方不启用。需要时可通过 conan requirement 补充并打开对应 `HTTPLIB_REQUIRE_*` 选项。

## 测试说明

### test_package 测试
- 文件: `test_package/test.cpp`
- 验证内容:
  1. `#include <httplib.h>` 头文件可被包含
  2. `httplib::Client` / `httplib::Server` 实例化
  3. `get_header_value` 默认值返回

## 验证结果

R01 首轮：conan create + test_package 消费者测试通过（1/1）。

## 注意事项

1. **Header-only 库特性**：无二进制产物，无需 ELF 签名 / RPATH
2. **CMake 目标**：安装后可通过 `find_package(httplib)` 和 `httplib::httplib` 目标链接
3. **C++ 标准**：要求 C++11 及以上
4. **可选能力**：HTTPS/Zlib/Brotli 默认关闭，按需开启
