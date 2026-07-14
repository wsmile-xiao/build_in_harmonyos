# opencl-headers

## 简介
OpenCL Headers 是 Khronos Group 维护的 OpenCL 标准 API 的 C 语言头文件包，定义了 OpenCL 的接口声明。

## OHOS 适配
- 纯头文件库（header-only），无需编译 .so
- 无外部依赖
- test_package 仅验证头文件可被 `#include` 和编译

## 依赖
- 无编译依赖
- 无运行时依赖

## 功能验证
```bash
# 编译测试程序（验证头文件可用）
clang test.c -o test_probe -I$CONAN_INCLUDE_DIRS_OPENCL_HEADERS
./test_probe
```

## 参考
- 主页: https://github.com/KhronosGroup/OpenCL-Headers
- OpenCL 注册表: https://www.khronos.org/registry/OpenCL/
