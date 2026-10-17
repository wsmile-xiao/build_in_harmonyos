# optional-bare 1.1.0 适配笔记

## 基本信息
- **上游**: https://github.com/martinmoene/optional-bare (tag v1.1.0)
- **许可证**: BSL-1.0 (Boost Software License)
- **类型**: header-only 单文件 C++98+ 精简版 optional（include/nonstd/optional.hpp）

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-31
- 编译器: clang/clang++ 15.0.4（HarmonyOS PC / aarch64，musl）
- 状态: built

## 编译步骤
conan 配方驱动（archives/o/optional-bare/1.1.0/conanfile.py）：
1. source() 下载官方 tarball（sha256 85eb623a…）
2. 无补丁，源码直接编译
3. CMake 配置：-DOPTIONAL_BARE_OPT_BUILD_TESTS=ON -DOPTIONAL_BARE_OPT_BUILD_EXAMPLES=OFF，
   CMAKE_SYSTEM_NAME=Linux（规避 E092 CMake 不识别 OHOS）
4. build() 编译上游 4 个标准变体测试（cpp98/cpp11/cpp14/cpp17）并运行 ctest
5. package() 仅拷贝 include/nonstd/optional.hpp 与 LICENSE.txt（header-library）

## 遇到的问题与解决方案

无。零依赖、零补丁库，首次尝试即通过全部门禁。

## 依赖版本
无任何依赖。测试框架 lest（test/lest_cpp03.hpp）为上游内置，无需联网。

## 验证结果

```bash
bash ci/scripts/preflight_check.sh optional-bare/1.1.0      # OK
python3 scripts/ohc-run.py conan-verify optional-bare 1.1.0 # G0-G4 + L2/L4/L5 全过
# 上游测试：4/4 ctest 变体（test-cpp98/11/14/17）全部 Passed
# test_package：16 条断言全过（cxx_std_14 下验证 nonstd 实现路径）
```

## 注意事项
- C++17 及以上该头文件自动切换为 std::optional 别名（上游设计）；
  test_package 用 cxx_std_14 确保验证的是 nonstd 实现
- header-only，package_id 清空（任意平台二进制等价）
---

**编译结束**: 2026-08-31 11:54
**最终状态**: built
