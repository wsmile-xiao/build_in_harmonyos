# safeint 3.0.28a HarmonyOS 适配笔记

## 编译环境

- 目标系统：HarmonyOS PC aarch64
- 构建系统：CMake / Conan 2.x
- 编译器：HarmonyOS Clang 15.0.4
- 软件形态：C/C++ 仅头文件库
- 外部依赖：无

## 源码身份

- 官方标签：`3.0.28a`
- 官方地址：`https://github.com/dcleblanc/SafeInt/archive/refs/tags/3.0.28a.tar.gz`
- SHA-256：`9e652d065a3cef80623287d5dc61edcf6a95ddab38a9dfeb34f155261fc9cef7`
- 标签内 `SafeInt.hpp` 注释写有内部版本 `3.0.28p`；Conan 版本按官方标签和任务版本使用 `3.0.28a`。

## 构建与适配

配方应用补丁后使用上游 CMake 工程，并显式构建 11 个 Clang 目标：3 个 SafeInt 运行时变体、1 个 C safe_math 运行时测试、6 个 C++ 标准/异常配置编译测试，以及 1 个 C safe_math 编译测试。包本身仅安装三个公开头文件和 MIT 许可证，不生成 `.a`、`.so` 或命令行程序。

OHOS SDK 在交叉编译时为 Clang 自动加入 `--gcc-toolchain`；上游测试的全局 `-Werror` 会将 Clang 的 `unused-command-line-argument` 警告升级为错误。配方仅把该特定诊断降级为普通警告，不关闭其他 `-Werror` 检查。

## 上游测试用例清点（R51）

上游根 CMake 工程在 Clang 测试目录注册 4 个 CTest：

| # | CTest 名称 | 覆盖内容 | HarmonyOS 结果 |
|---|------------|----------|----------------|
| 1 | `SafeIntTest_clang` | 默认实现及完整算术向量 | 通过 |
| 2 | `SafeIntTest_clang_NoIntrinsic` | 禁用 intrinsics 和 int128 的回退实现 | 通过 |
| 3 | `SafeIntTest_clang_NoInt128` | 禁用 int128 的实现 | 通过 |
| 4 | `safe_math_test_clang` | C safe_math 完整算术向量 | 通过 |

上游另有 7 个只以“成功编译”为通过条件的 Clang 目标；适配后全部构建成功，但不重复计入上游 CTest 用例数。宿主机上游实测为 GCC CTest 4/4；HarmonyOS 适配后保留同等的 4/4 正式运行测试，没有减少分母。

## 上游测试修改

补丁 `0001-Test-CompileTest.cpp.patch` 只修改 `Test/CompileTest.cpp`：

1. 将 C++17 标准库 include 和辅助模板移到文件作用域，避免在函数体内声明命名空间/模板。
2. C++98 目标使用普通枚举和非限定枚举值；C++11 及以后仍使用原有 scoped enum。

修改只修复编译测试在其声明标准下的语法，不删除测试、不改变断言和运行时测试向量。

## 新增消费者与 HarmonyOS 测试

- `test_safeint.cpp`：10 个 C++ SafeInt 构造、算术、转换、溢出检测和异常检查。
- `test_safe_math.c`：8 个 C safe_math 转换、加减乘除及溢出检查。
- `test_safeint_ohos.cpp`：7 个 HarmonyOS 专有检查，验证 `__OHOS__`、aarch64 LP64、Clang/int128 分支及 64 位乘法溢出路径。

新增测试共 3 个可执行用例、25 个显式检查；加上上游 4 个 CTest，适配后测试总数为 7，不少于上游实测 4。

## 验证命令

```bash
conan create archives/s/safeint/3.0.28a -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
CI_PACKAGES="archives/s/safeint/3.0.28a" zsh ci/conan/build_and_test.sh
```

真机验证要求：上游 CTest `4/4`、消费者 CTest `3/3`、显式消费者检查 `25/25` 全部通过。
---

**编译结束**: 2026-09-18 10:05
**最终状态**: built
