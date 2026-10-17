# libsoxr (SoX Resampler)

## 简介
High quality, one-dimensional sample-rate conversion library

## OHOS 适配
- 老 CMakeLists → -DCMAKE_POLICY_VERSION_MINIMUM=3.5
- 关 openmp/tests/examples/lsr-bindings
- doc 装到 CMAKE_INSTALL_FULL_DOCDIR 绝对路径 → configure 就设 -DCMAKE_INSTALL_PREFIX=<pkg>

## 依赖
- 无 conan 依赖（仅系统库）
- 编译工具: clang, cmake

## 参考
- 官网: https://sourceforge.net/projects/soxr/
