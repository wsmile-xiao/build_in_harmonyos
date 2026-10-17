# nnom

> 面向微控制器的神经网络库：在资源受限的嵌入式设备上构建并运行量化（定点）神经网络模型。
> 纯 C 语言实现，Apache-2.0，官方仓库 https://github.com/majianjia/nnom

## 简介

nnom 是 majianjia/nnom 的 HarmonyOS PC 适配版本（v0.4.3，Apache-2.0）。
上游源码包含 `src/{core,layers,backends}/*.c`、`inc/`（公共头 + `layers/` 子目录）与
`port/nnom_port.h`，**没有独立构建系统**（仅提供面向 RT-Thread/SCons 的 SConscript），
本适配以 `static-library` Conan 配方直接编译全部 31 个 C 源文件为静态库。

## OHOS 适配要点

- **零构建系统直接编译**：`clang -c -O2 -fPIC -std=c99` 逐文件编译
  `src/core|layers|backends/*.c`，`llvm-ar rcs` 打包 `libnnom.a`
  （R33 合规：编译器取自 Conan conf，不裸用 shell 变量）。
- **定点类型自给自足**：`q7_t/q15_t/q31_t/q63_t` 由 `inc/nnom.h` 自身 typedef
  （`int8_t/int16_t/...`），不依赖 CMSIS 头；`arm_math.h` 仅在
  `NNOM_USING_CMSIS_NN` 定义时引入（本配方不定义），因此无需 ARM CMSIS 依赖。
- **双目录头文件安装**：`inc/*.h` 平铺到 `include/`，`inc/layers/*.h` 保留
  `include/layers/` 子目录（`nnom_layers.h` 以 `#include "layers/xxx.h"` 相对包含），
  `port/nnom_port.h` 平铺到 `include/` 根（`nnom.h` 以 `#include "nnom_port.h"` 引入）。
- **libm 依赖**：激活函数使用 `tanh/round` 等数学函数，`cpp_info.system_libs = ["m"]`。
- **上游测试**：官方 tag 无独立 TEST_CASE/测试框架注册；`examples/auto_test`
  为需 Keras/TensorFlow+SCons 的端到端样例（该环境不可得，样例逐项实测并记录
  首错与恢复条件，全量通过率如实填报 0/0）；消费者用例（test_nnom.c）与鸿蒙专项
  用例（test_ohos.c）由 test_package 自编提供，ctest 2/2 通过（层经 model->add
  链接、显式运行时校验，输出 20/-20/0 均实证一致）。

## 依赖

无第三方依赖（纯 libc + libm：stdio/stdlib/string/math）。
