# zlib-ng

## 简介
zlib 的下一代替代版本，针对现代 CPU 进行性能优化。本包提供 **zlib-ng 原生 API**（`zng_*` 函数、`<zlib-ng.h>` 头、`libz-ng.a` 库）。

> 如需 zlib 兼容 API（`<zlib.h>`、`libz.a`）请用 [zlib-ng-compat/2.3.3](../zlib-ng-compat/2.3.3)。

## OHOS 适配
- CMake 构建
- `ZLIB_COMPAT=OFF`：输出 zlib-ng 原生 API（`libz-ng.a`、`zlib-ng.h`）
- `BUILD_SHARED_LIBS=OFF`：静态构建，避免 OHOS .so 签名复杂度
- `WITH_GTEST=OFF`：跳过上游 GoogleTest 构建
- zlib-ng 非系统同名库（系统同名库为 `zlib`/`libz`），静态构建不影响系统

## 用法
```cmake
find_package(zlib-ng REQUIRED CONFIG)
target_link_libraries(your_target zlib-ng::zlib-ng)
```
```c
#include <zlib-ng.h>
zng_compress(...);   /* 原生 zlib-ng 压缩 API */
```

## test_package
- `test_package/test.c`：验证 `ZLIBNG_VERSION` + `zng_compress`/`zng_uncompress` 压缩解压往返
- 输出 `PASS: zlib-ng native API is functional`

## 参考
- 源码: https://github.com/zlib-ng/zlib-ng
- 兼容版本: [zlib-ng-compat/2.3.3](../zlib-ng-compat/2.3.3)
