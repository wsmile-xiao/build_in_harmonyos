# opencl-headers 2026.05.29 — 鸿蒙 PC conan 制品

`os=OHOS, arch=armv8`(= aarch64)的 conan 包，纯头文件库。

## 出包（鸿蒙 PC CI）

```bash
# 鸿蒙 PC 设备原生 conan create
conan create . -pr ohos-native
```

> 源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验（`source()` 用 `get()`）。

## 前提

> 所用 conan 的 settings 须含 `os=OHOS`（大写）。stock conan 2 默认不含 OHOS，参考 lerc/README.md 的扩展方式。

## 特点

- 纯 header-only，无 .so 产物，无签名步骤
- 无编译依赖
- test_package 仅验证头文件可被 `#include <CL/opencl.h>` 编译

## 消费 A：conan 工程（CMake 消费）

```bash
conan install --requires=opencl-headers/2026.05.29 -pr ohos-native
```

## 消费 B：裸程序（设备 ~/usr/local）

```bash
conan install --requires=opencl-headers/2026.05.29 -pr ohos-native \
    --deployer=usr_local --deployer-folder=$HOME/usr/local
```

头文件展开到 `~/usr/local/include/CL/`；`#include <CL/opencl.h>` 即可命中。
