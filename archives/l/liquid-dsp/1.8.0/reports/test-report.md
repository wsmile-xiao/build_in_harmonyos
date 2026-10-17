# liquid-dsp 1.8.0 验证报告

## 验证环境

- 设备：HarmonyOS PC 真机（aarch64）
- 架构：AArch64 (armv8)
- 编译器：clang 15.0.4 / clang++（OHOS，libc++，C++17）
- 构建工具：CMake 4.1.2、GNU Make 4.4.1
- 构建选项：`BUILD_SHARED_LIBS=OFF`、`BUILD_STATIC_LIBS=ON`、
  `BUILD_EXAMPLES=OFF`、`BUILD_AUTOTESTS=ON`、`BUILD_BENCHMARKS=OFF`、
  `FIND_FFTW=OFF`（使用内置 FFT 实现，无外部依赖）

## 构建与安装

- 上游源码配置：CMake configure 成功，aarch64 真机自动启用 NEON 加速
  （SSE/AVX/AVX512/AltiVec 均为 No，Threads=Yes，FFTW=No）。
- 构建结果：libliquid.a 静态库 + xautotest 全部构建成功（100%）。
- 安装结果：`include/liquid/liquid.h`、`lib/libliquid.a`、
  `lib/cmake/liquid/liquidConfig.cmake`、`lib/pkgconfig/liquid-dsp.pc`。

## 上游测试（autotest）

```text
tests  : pass=1341  fail=0  skip=0
checks : pass=716520 fail=0
overall: PASS
```

1341 个测试 / 716520 个断言全部通过，无失败、无跳过。

## 消费者测试（test_package）

使用 `liquid::liquid-static` 导出目标，编译并运行以下断言：

1. `liquid_nextpow2(100) == 7`（2^7=128，向上取整的对数）。
2. `liquid_version` 字符串非空且等于 `1.8.0`。
3. `windowf_create(16)` 创建成功；push 16 次 1.0f 后
   `windowf_read` 返回的窗口首元素为 1.0f。

结果：3/3 通过，退出码 `0`（`ALL PASS`）。

## 补丁

- `0001-cmakelists-static-config.patch`：静态-only 构建时上游把 LIBNAME
  重命名为 `liquid-static`，但 `cmake/Config.cmake.in` 引用的是
  `@PROJECT_NAME@`（=liquid），导致生成的 `liquidConfig.cmake` 与
  实际安装的 `liquid-staticTargets.cmake` 命名不一致、且 include 目录
  指向不存在的 `include/liquid-static`，`find_package(liquid)` 失败。
  补丁注释掉该重命名，保持 LIBNAME=liquid，修复静态库的 CMake 包
  配置一致性。已用独立 consumer 工程验证 `find_package(liquid CONFIG
  REQUIRED)` + `target_link_libraries(... liquid::liquid-static)` 可用。

## 源码与校验

- 源码：`https://github.com/jgaeddert/liquid-dsp/archive/refs/tags/v1.8.0.tar.gz`
- SHA256：`abef8b2ddfd58c0a84ecda4f62158c4824b916144af4a2b07776e1a144d8cda4`
- SHA512 与 vcpkg 官方记录一致：`83c55bf8...`

## 测试边界

conan-verify G0-G4 门禁与 L2/L4/L5 全 PASS；test_package 在 OHOS
真机（非交叉编译）上直接运行消费者二进制并通过。
