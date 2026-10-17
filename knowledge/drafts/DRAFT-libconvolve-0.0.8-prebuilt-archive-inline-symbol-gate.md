# 旧 C 源包预带静态归档时的重建与 `inline` 符号门禁

> 草稿，等待知识库维护者审查；触发项目：libconvolve 0.0.8，HarmonyOS PC AArch64 / Clang 15 / Conan 2.29.1，2026-09-25。关联适配 PR：[#12716](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/12716)。

## 问题与风险

libconvolve 0.0.8 的官方源码压缩包自带预编译的 `libconvolve.a`。上游 Makefile 又按时间戳判断是否重编译，因此仅看到 `make libconvolve.a` 成功或归档文件存在，不能证明包中是鸿蒙目标架构的新产物。该项目的 `complex_mul.c` 定义 `void inline complex_mul(...)`，其他目标文件跨翻译单元调用它；不同 C inline 语义决定归档是否提供外部定义。静态归档允许保留未解析引用，缺符号通常在最终消费者链接时报错，也可以用 `llvm-nm` 提前识别归档缺少对应定义。

本次源包经 SHA-256 `60701b9da1af63fa6883df8fadd8d474af370f63df18481dea903097771781d4` 固定；压缩包目录确认含 `libconvolve.a`。这说明有复用旧归档的风险；**未声称本次实际发生了错误架构归档被打包**。

## 目标机实测：符号语义

在同一 HarmonyOS PC 设备、同一 `complex_mul.c` 和 FFTW 头文件上，用 Clang 编译到两个独立的探针目标文件。以下为目标机实测命令与关键输出；`<fftw3f/include>` 表示 Conan 依赖包的实际 include 目录：

```sh
clang -std=c99 -O2 -c complex_mul.c -I<fftw3f/include> \
  -include fftw3.h -include complex_mul.h -o probe-inline-c99.o
llvm-nm probe-inline-c99.o
# 没有 complex_mul 条目

clang -std=c99 -fgnu89-inline -O2 -c complex_mul.c -I<fftw3f/include> \
  -include fftw3.h -include complex_mul.h -o probe-inline-gnu89.o
llvm-nm probe-inline-gnu89.o
# 0000000000000000 T complex_mul

llvm-nm convolution_process.o | grep complex_mul
#                  U complex_mul

llvm-nm libconvolve.a | grep complex_mul
# complex_mul.o: 0000000000000000 T complex_mul
# convolution_process.o:                  U complex_mul
```

`T` 是目标文件中的外部定义，`U` 是调用方的未解析引用。上游 `complex_mul.h` 也写了 `void inline` 声明。本条结论只针对该确切声明/定义形式和 Clang 15 探针；不推广为“所有 C99 inline 都不导出”。例如已有草稿 `DRAFT-hash-0.0.1-clib-inline-symbol-key-pointer` 记录了头文件普通原型配合 C99 `inline` 时产生外部 `T` 的不同情形。

## 已实施的修复与验证

1. Conan 配方使用 `make -B -j1 libconvolve.a`，忽略预带归档的时间戳并以目标编译器重建所有目标文件；不把官方压缩包里的归档直接装包。
2. 编译参数加入 `-fgnu89-inline`，维持这个旧源码所需的外部符号；归档中 `complex_mul.o` 的 `T complex_mul` 与调用方 `U complex_mul` 配对。
3. 用包安装后的公共头文件与 `libconvolve.a` 构建并运行 `test_package` 消费者，而非仅以构建阶段成功为依据。真机最终 `conan create` 返回 0；原上游 ringbuffer 烟雾测试 1/1、消费者集成测试 1/1。完整日志保留本地，SHA-256 `046e147c9ef10b423567bee950586f345afddd5c8734f0e81f5a367bd5a28ab3`，按仓库规则未纳入 PR。

从配方所在仓库根目录，在已配置 `ohos-aarch64` profile 与 `ohpcd` 远端的目标机上复验时使用：

```sh
conan create archives/l/libconvolve/0.0.8 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=libconvolve/0.0.8 -r=ohpcd
```

`--build=libconvolve/0.0.8` 强制重建本包；`--build=missing` 可能直接复用缓存，不能作为这项检查的替代。配方内实际的 `make -B -j1` 同时避免预带归档和目标机 GNU Make 并行 FIFO 问题。前述独立 `llvm-nm` 探针是作者目标机实测，不属于 `conan create` 日志内容。

推荐检查顺序：核对来源压缩包是否预带制品 → 强制目标端重建 → 用 `llvm-nm` 对照定义与引用 → 以真正的包消费者完成最终链接与运行。若消费者同时需要公开头文件依赖，还须独立核查 Conan `transitive_headers`；这部分已有 E480 覆盖，并非本草稿的新颖性主张。

## 适用边界与查重

- 适用：旧 Makefile 源包自带预构建 `.a`，并有跨翻译单元 `inline` 调用；静态归档“构建成功”可能掩盖符号或架构问题。
- 不适用：`static inline` 只在本翻译单元使用、上游已显式导出非 inline 定义，或包是纯头文件。
- 与 `DRAFT-hash-0.0.1-clib-inline-symbol-key-pointer` 的重叠：都强调用 `llvm-nm` 实证 inline 符号；区别是本案 C99 无外部定义、GNU89 有定义，并且源包预带归档需强制重编译，再经消费者链接验收。与 E420 的旧 C 声明问题、E480 的 FFTW 公共头传递也仅部分相邻。维护者若认为这些差异不足以成为独立 B 路径条目，可以合并进现有知识，而不应重复计分。

这是一份供评审的候选知识，不代表路径 B 已受理、CI 已通过或积分已发放。
