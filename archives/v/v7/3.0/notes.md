# v7 3.0 适配笔记

## 编译环境

- 上游仓库：<https://github.com/cesanta/v7>
- 上游标签：`3.0`，tag commit `872221b463666b514e10283873da1c307a634ba0`
- 源码归档：`https://github.com/cesanta/v7/archive/refs/tags/3.0.tar.gz`
- SHA256：`17a15891037dd6f8a0e39f8a9f601feb0f9b8d0def12afe630b705831e6b5cc5`
- 构建系统：顶层 raw Makefile，无 configure/CMake/CTest
- Conan 依赖：无
- 当前状态：`built`；设备 Conan、上游 runner、ECMA harness、静态库和消费者验证已执行。

## 编译步骤

配方从 `tools.build:compiler_executables` 读取 C 编译器、`llvm-ar` 和
`llvm-ranlib`，计划在源码目录串行执行：

```text
make -j1 CC=<conan-c-compiler> CFLAGS_EXTRA=-DV7_FILENAMES_SUPPRESS_CFUNC_ADDR v7
make -j1 CC=<conan-c-compiler> CFLAGS_EXTRA=-DV7_FILENAMES_SUPPRESS_CFUNC_ADDR test
<conan-c-compiler> -fPIC ... -c v7.c -o <build>/v7.o
<conan-ar> rcs <build>/libv7.a <build>/v7.o
<conan-ranlib> <build>/libv7.a
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游默认测试的 `test_exec_generic` 堆栈字符串包含随机 `cfunc_0x...` 地址 | 上游测试期望地址被抑制，源码已有对应编译宏 | 通过 Makefile 的 `CFLAGS_EXTRA` 传入 `-DV7_FILENAMES_SUPPRESS_CFUNC_ADDR`，不修改上游测试源码 |

## 源码修改

应用 `0001-use-writable-parser-test-paths-on-ohos.patch`：上游 parser 测试
固定写入只读 `/tmp/got_ast`，补丁改为运行时读取 POSIX `TMPDIR`（设备上为
可写的用户临时目录），并保留 `/tmp` 作为未设置时的回退；不引入平台条件
编译宏，也没有修改测试逻辑。配方仍使用上游 Makefile 提供的
`CFLAGS_EXTRA` 入口。

## 依赖版本

- Conan host/build 依赖：无
- OHOS 设备工具已核对：Clang 15.0.4、Conan 2.29.1；归档器和 ranlib 由目标 profile 提供。

## 验证结果

本地 macOS 原生基线已执行：

```text
make -j1 test CFLAGS_EXTRA=-DV7_FILENAMES_SUPPRESS_CFUNC_ADDR
```

上游 runner 输出 `PASS, run 25790`。同一运行的 ECMA corpus 报告为
`6759 PASS / 4264 FAIL / 89 SKIP`，共 11112 cases（60.83%）；不把 harness
顶层返回成功误写成 ECMA corpus 全部通过。

本地 macOS 还用同一上游头文件和静态库构建了 `test_package/test_v7.c`，输出
`v7 consumer test: PASS`；这是消费者基线，不替代 OHOS 设备验证。

修复提交 `d728ab0ab6446e17f419d501825180189b26c51d` 已在设备端复核。设备执行：

```text
conan create archives/v/v7/3.0 --version=3.0 --profile=ohos-aarch64 --build=missing
```

结果为 Conan package、上游默认 23 个 unit suites、静态库打包和 consumer
均完成；设备日志为 `$HOME/tmp/import-deps-100-odd-v7-create-r6.log`。
上游 runner 输出 `PASS, run 25790 in 68.323s`。ECMA harness 报告覆盖率
为 60.83%（6759/11112），其中 4264 条 corpus 行标记 `FAIL`、89 条标记
`SKIP`；harness 进程返回 0，不能把这 11112 条数据写成全量通过。
`test_package` 输出 `v7 consumer test: PASS`。

## 注意事项

- 上游源码注册 28 个 `RUN_TEST` suite，其中默认启用并执行 23 个，另有 5 个可选 suite 未注册。
- CTest 注册数为 0；ECMA corpus case 数独立于 suite 数统计。
- `v7` 同时是静态库和命令行执行器，因此需要软件级 `commands.json`。
