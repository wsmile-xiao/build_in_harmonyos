# inja 3.5.0 适配笔记

## 编译环境

- 构建系统：CMake
- 目标：HarmonyOS aarch64
- 编译器：OHOS Clang 15.0.4
- 状态：built

## 适配内容

使用官方 v3.5.0 源码归档，启用 C++17、嵌入式 nlohmann JSON、安装规则和上游
测试，关闭外部 `nlohmann_json` 查找。包为 header-only，CMake consumer target
为 `pantor::inja`。

## 测试用例核对

- `test/test.cpp` 聚合了 15 个 doctest 测试用例和 258 个断言。
- Conan 构建执行 `inja_test` 与 `single_inja_test` 两个上游 CTest target，设备端
  2/2 通过；本地原生运行也得到 15/15、258/258。
- `test_package/test_inja.cpp` 是 1 个消费者用例，覆盖 render、Environment、
  loop、conditional 和 RenderError，共 4 个断言。

## 验证

```bash
conan create archives/i/inja/3.5.0 \
  --profile:host=ci/conan/profiles/ohos-aarch64 --profile:build=default \
  --build="*" -c tools.build:jobs=1
```

设备端源码构建、两个上游测试目标、header/CMake 安装和消费者编译执行均通过，
退出码为 0。

### 对话 #1

- 设备 W3：`W3_RC=0`。
- 上游 CTest target：`2/2` 通过。
- 消费者测试：`1/1` 通过，4 个断言满足。
---

**编译结束**: 2026-09-01 15:01
**最终状态**: built
