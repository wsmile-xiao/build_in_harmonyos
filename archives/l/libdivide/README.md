# libdivide

## 简介
libdivide 是一个 header-only 的 C/C++ 库，用于优化整数除法。它将昂贵的整数除法指令替换为更廉价的乘法、移位和加法序列。编译器通常只在除数为编译期常量时做此类优化，libdivide 让你在运行时也能获得同样的加速。

此外 libdivide 支持 SIMD 向量除法（SSE2 / AVX2 / AVX512 / ARM NEON），这在 SIMD 指令集中尤其有用，因为 SIMD 通常缺少整数除法指令。

- 上游：https://github.com/ridiculousfish/libdivide
- 许可：Boost Software License 或 zlib License（任选其一）

## OHOS 适配
- header-only 库，只需把 `libdivide.h` 复制到 `include/`，无需编译产物
- Conan 配方使用 `package_type="header-library"`，`package()` 直接 `copy()` 头文件
- 上游 CMake 在 AArch64 上自动检测并启用 NEON；交叉编译路径使用 `check_cxx_source_compiles`（非 `try_run`），OHOS aarch64 工具链兼容
- test_package 仅测试最基础、跨平台的 scalar divider API，不强制启用任何 x86 专用 SIMD 路径

## 依赖
- 编译依赖：无（header-only）
- 运行依赖：无

## 功能验证
```bash
# 编译测试（header-only，只需 include 路径）
echo '#include <libdivide.h>
int main() {
    libdivide::divider<int> d(7);
    return d.done(100) == 14 ? 0 : 1;
}' > test.cpp
clang++ -std=c++11 -I include test.cpp -o test && ./test && echo "OK"
```

## 参考
- GitHub：https://github.com/ridiculousfish/libdivide
- 文档：https://github.com/ridiculousfish/libdivide/tree/master/doc
