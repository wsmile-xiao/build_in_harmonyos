# libdisorder 0.0.2-git20130809.8062ee1 HarmonyOS PC 适配记录

## 上游与源码

- 上游：https://github.com/locasto/libdisorder
- 版本：`code/VERSION` 为 `0.0.2`，固定提交 `8062ee1514f939c9013da234f1c37ef06fa66a80`（2013-08-09）。
- 源码归档 SHA-256：`1a5d90973b7d4abf547a1d45fa2bbf99845d990455edea56ef7fb0c9b2a7d14b`。
- 语言预检结果：C 源文件 3/3，主体比例 100%，与 C/C++ 赛道兼容。

## 适配方案

上游 `code/src/Makefile` 硬编码 `gcc`、`ar` 与 `/usr`，不适合交叉编译。Conan 配方不改动上游源码，从 `tools.build:compiler_executables` 获取 C 编译器，并从同一工具目录选取 `llvm-ar`/`llvm-ranlib`，生成：

- `lib/libdisorder.a`
- `include/disorder.h`
- `bin/ropy`
- `licenses/COPYING`

库使用 `log2`，所以在 Conan `package_info()` 中向消费者传播系统库 `m`。此库使用全局统计状态，上游 API 本身不保证线程安全，本次适配不改变该语义。

## 上游测试审计

上游只有 `code/test/test.c` 一个测试程序：它持续读取 `/dev/urandom`，每轮计算 16384 字节的熵并刷新一行输出，没有退出条件或断言框架。配方原样编译该文件，实际运行后要求连续获得 3 轮格式正确、序号连续且熵/最大熵/比率均在有效范围的结果，然后向无限循环发送终止信号。此处按上游可执行程序口径计为 1 个测试，通过数必须为 1/1。

## 消费者测试

- `test_api.c`：验证空输入、二元/四元均匀分布、256 字节全集、非均匀分布以及所有状态访问 API。
- `test_ropy.py` 逻辑内嵌于 test_package：用固定 `aabb` 文件验证打包后命令行工具的 token、entropy、metric、maxent 和 ratio。
- `test_ohos.c`：HarmonyOS 专有测试，编译期确认 `__OHOS__` 与 AArch64，运行期读取 `/dev/urandom` 并用被测库校验熵值范围。

适配后共 3 个独立测试，不少于上游实测的 1 个，且包含 1 个 HarmonyOS 专有测试。

## 补丁与依赖

- 补丁：无。
- Conan 三方依赖：无。
- 系统库：`libm`。
---

**编译结束**: 2026-09-18 04:00
**最终状态**: built
