# nanobench 4.6.0 适配笔记

## 编译环境

- 构建系统：CMake
- 目标：HarmonyOS aarch64
- 编译器：OHOS Clang 15.0.4
- 状态：built

## 适配内容

使用官方 v4.6.0 源码归档，启用上游 benchmark/test executable，按 C++11 构建并
安装 `libnanobench.a`、`nanobench.h` 和 CMake 配置。Conan package type 标为
`static-library`，consumer target 为 `nanobench::nanobench`。

## 测试用例核对

- 实际源码包含 49 个测试源文件、150 个 `TEST_CASE` 声明；C++11 配置注册 147
  个，另有 3 个 C++17-only 声明不编译。
- HarmonyOS 设备执行上游程序得到 `145 passed / 2 skipped / 0 failed`，
  `32071/32071 assertions`。两个 skip 是上游显式的硬件能力和 C++17 条件，未计为失败。
- `test_package/test.cpp` 是 1 个消费者用例，使用真实 `Rng` 和 `Bench` 执行，
  共 2 个检查。

## 验证

```bash
conan create archives/n/nanobench/4.6.0 \
  --profile:host=ci/conan/profiles/ohos-aarch64 --profile:build=default \
  --build="*" -c tools.build:jobs=1
```

设备端源码构建、上游 benchmark/test executable、静态库安装和消费者编译执行均
通过，退出码为 0。

### 对话 #1

- 设备 W3：`W3_RC=0`。
- 上游 doctest：145 passed、2 skipped、0 failed、32071 assertions。
- 消费者测试：`nanobench consumer: PASS`。
---

**编译结束**: 2026-09-01 15:01
**最终状态**: built
