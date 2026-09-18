# libfixmath 0-20220222 HarmonyOS PC 适配笔记

## 源码与依赖

- 上游仓库：https://github.com/PetteriAimonen/libfixmath
- 固定版本提交：`64d851a6f93267defcdc11cfaee4102786c660bb`
- 源码 SHA-256：`475e2e0d7fff0fa9a7471d96de8bb930808345848ed4db729dba0557e3ea2407`
- 构建系统：CMake
- 依赖审计：库本体无第三方依赖；仅测试与上游辅助程序使用系统 C 数学库。
- HarmonyOS 编译器：OHOS Clang/Clang++ 15.0.4，目标为 AArch64。

## 适配实现

上游无需源码补丁即可由 HarmonyOS SDK 交叉编译。Conan 配方固定生成静态库，完整运行上游 CTest 测试矩阵，并将 `libfixmath` 的 C/C++ 公开头文件、MIT 许可证和 `liblibfixmath.a` 打包。由于上游没有 CMake 安装规则，打包步骤使用 Conan 文件复制 API 明确构造包布局。

## 测试口径

上游 `tests/tests.cmake` 定义 12 个 CTest 项，分别覆盖 64 位、32 位与 8 位查表配置，以及溢出检查、舍入选项的组合：

`tests_ro64`、`tests_no64`、`tests_rn64`、`tests_nn64`、`tests_ro32`、`tests_no32`、`tests_rn32`、`tests_nn32`、`tests_ro08`、`tests_no08`、`tests_rn08`、`tests_nn08`。

每个测试程序执行 abs、add、mul、div、sub、sqrt、lerp、macros 共 8 组有效测试，因此 12 个上游测试项对应 96 组测试执行。上游源码与测试均未修改。

消费侧新增两个独立 CTest 项：

1. `test_libfixmath_cpp_api`：从 Conan 包使用 C++ 包装类与 C API，校验转换、四则运算、平方根、指数、插值、三角函数和字符串往返。
2. `test_libfixmath_ohos_abi`：HarmonyOS 特有测试，在编译期校验 OHOS/AArch64/musl/小端 ABI，在运行期校验类型宽度、负数运算、除法和字符串转换。

## 验证命令与结果

```bash
conan create archives/l/libfixmath/0-20220222 \
  -pr:h=ohos-aarch64-linux-cross -pr:b=linux-x86_64 --build=missing

python3 scripts/ohc-run.py finish libfixmath 0-20220222 built
```

- 上游测试：12/12 通过（96/96 有效测试组通过）。
- C++ 消费测试：1/1 通过。
- HarmonyOS 特有测试：1/1 通过。
- Conan 创建、打包与消费验证：全部通过。

## 常见不规范复核

已按赛事常见合入不规范清单复核：归档路径、软件名与版本号规范；只包含当前版本交付文件；未混入框架或汇总文件改动；无占位符、无源码镜像、无构建产物、无无效补丁；配方包含四项 Conan 设置并执行完整上游测试；测试包真实调用公开 API。
---

**编译结束**: 2026-09-14 10:01
**最终状态**: built
