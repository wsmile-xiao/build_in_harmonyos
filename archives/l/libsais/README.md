# libsais

## 简介
libsais 提供基于 induced sorting 算法的线性时间后缀数组（SA）、广义后缀数组（GSA）、最长公共前缀数组（LCP）、置换 LCP（PLCP）、Burrows-Wheeler 变换（BWT）及逆 BWT 构造，并可选 OpenMP 多核并行加速。

## OHOS 适配
- 上游 CMake 构建（`cmake` + `make`），无需补丁。
- 目标平台为 OpenHarmony aarch64，关闭非必要的 OpenMP 并行；上游 2.10.4 不含 x86 SIMD / 汇编分支，无平台特定 SIMD 适配需求。
- 默认构建为静态库（`LIBSAIS_BUILD_SHARED_LIB=OFF`），与上游默认一致。

## 依赖
- 无编译依赖（纯 C99，标准库即可）。

## 功能验证
```bash
# 检查库安装
ls -la $HOME/usr/local/lib/libsais*
```

## 参考
- 主页: https://github.com/IlyaGrebnov/libsais
