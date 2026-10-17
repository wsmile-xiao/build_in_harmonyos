# HarmonyOS CMake feature probes and upstream runtime golden values need separate gates

- 路径：B（知识库扩展）
- 来源：tlfloat 1.15.0，真实 HarmonyOS aarch64 设备
- 适用范围：使用 CMake `try_compile`、long-double 探测或宿主生成 golden
  values 的 C/C++ 数值库配方

## 规则

在 OHOS 配方中把必须影响项目条件分支的选项写入
`CMakeToolchain.cache_variables`，并把探测设为
`CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`。对缺少 glibc long-double
符号的 libc++，显式关闭 binary128 long-double 假设。上游测试目标仍应编译，
但如果运行时基线依赖宿主 libc/ABI，应以独立的安装后消费者测试作为 OHOS
包门禁，并记录实际上游通过/失败数量。

## 证据

tlfloat 源码清点为 22 个测试条目；HarmonyOS 默认配置选择并成功编译其中 12 个
CTest 可执行文件，直接运行得到 7/12，五项失败均为 hash、格式化长度或 C++11
`sin` golden 差异，另 10 项为未启用的 exhaustive、MPFR 或 CUDA 可选条目。
安装消费者的 8/8 契约断言通过；另一个真实消费者流程使用 `tlfloat::Double` 执行
36 个月储蓄投影，并经 `tlfloat_snprintf` 输出 `5796.62`。CTest 2/2 通过，两个
消费者程序亦由 Conan 直接执行。未修改库 API；补丁只为测试提供 `std::pow` 替代
缺失的 `exp10`。

## 禁止

- 不要把 `tc.variables` 当成项目 cache 选项的等价替代。
- 不要把宿主 golden-value CTest 的失败改写成“未发现测试”或虚报全通过。

关联：`SET_LONGDOUBLE_IS_FLOAT128`、`CMAKE_TRY_COMPILE_TARGET_TYPE`、OHOS libc++。
