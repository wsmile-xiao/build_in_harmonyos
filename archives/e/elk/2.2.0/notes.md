# elk 2.2.0 适配笔记

## 编译环境

- 构建系统：Makefile
- 目标：HarmonyOS aarch64
- 编译器：OHOS Clang 15.0.4
- 状态：built

## 适配内容

使用官方 2.2.0 源码归档，将 `elk.c` 编译为 `libelk.a`，通过 `elk::elk` CMake
target 暴露静态库，并声明数学库依赖。配方从 Conan profile 读取 clang/llvm-ar，
同时把 clang 传给上游 test Makefile，避免 OHOS 环境没有 `cc` 别名。

## 测试用例核对

- 上游 `test/unit_test.c` 注册 12 个逻辑测试函数，活跃代码包含 374 个
  `assert()`；另有 9 个位于 `#if 0` 的禁用断言不计入。设备端 `make -C test test`
  通过。
- `test_package/test_elk.c` 是 1 个消费者用例，实际调用引擎创建、算术求值和状态
  求值 API，共 3 个检查。

## 验证

```bash
conan create archives/e/elk/2.2.0 \
  --profile:host=ci/conan/profiles/ohos-aarch64 --profile:build=default \
  --build="*" -c tools.build:jobs=1
```

设备端静态库源码构建、上游测试、安装和消费者编译执行均通过，退出码为 0。

### 对话 #1

- 设备 W3：`W3_RC=0`。
- 上游测试：`SUCCESS. All tests passed`。
- 消费者测试：`Elk 2.2.0 API smoke test: PASS`。
---

**编译结束**: 2026-09-01 15:01
**最终状态**: built
