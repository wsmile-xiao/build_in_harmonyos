# trompeloeil

> Header-only C++ mocking framework (Boost Software License 1.0) — 把 mock 期望变成编译期与运行期可测试的行为。

## 简介

trompeloeil 是一个单头文件（C++11/14/17/20）的 C++ mock 框架：`MAKE_MOCKn` 生成 mock 类的方法，`REQUIRE_CALL` / `ALLOW_CALL` / `FORBID_CALL` 声明期望，支持参数匹配器（`gt`/`re`/`_` 等）、基数（`.TIMES`）、序列（`.IN_SEQUENCE`）、副作用（`.LR_SIDE_EFFECT`）、C++20 协程（`CO_RETURN`/`CO_YIELD`/`CO_THROW`）。它是一个“负向测试也参与断言”的框架：`compilation_errors/` 下 68 个翻译单元必须编译失败且诊断文本匹配声明正则。

本归档提供 HarmonyOS PC（OHOS aarch64，OHOS SDK clang 15.0.4 / libc++ 15）上的 header-only 消费方式：`conan install` 后通过包内 `include/trompeloeil.hpp`（含各测试框架适配头）直接使用，CMake 目标名为 `trompeloeil::trompeloeil`。

## OHOS 适配要点

- 纯头文件：产物为 `include/`（`trompeloeil.hpp` + `trompeloeil/*.hpp` + catch2/gtest/doctest/boost 等适配头）+ 许可证；无 `.a`/`.so`。
- 上游自测需要 Catch2 v3：配方以 `tool_requires catch2/3.8.1` 提供并在 `build()` 内编译运行，避免 `test/CMakeLists.txt` 在找不到 Catch2 时**构建期从 GitHub 下载 catch.hpp**。
- 68 个负向编译用例由配方内的线程池驱动 `verify_compilation_error.sh`（OHOS 无 GNU `parallel`）；`TMPDIR` 指向构建目录（OHOS `/tmp` 只读）。
- 上游测试在 C++14 与 C++20 两个标准上全量真实执行（C++20 含协程用例），并作为 `conan create` 的内置门禁。

## 排除与替代

无（库类型，无命令行工具，不需要 `commands.json`）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| 无 | - | 运行时零依赖（header-only） |
| catch2 | 3.8.1 | 仅上游自测与消费者测试使用（构建期） |

## 功能验证

```cpp
#include <trompeloeil.hpp>

struct mock_fs {
  MAKE_MOCK1(open, int(const char*));
};

mock_fs fs;
REQUIRE_CALL(fs, open(trompeloeil::_)).TIMES(1).RETURN(0);
int fd = fs.open("/tmp/x");
```

```bash
# 消费者编译（conan 包已 install）
clang++ -std=c++14 -I<trompeloeil包>/include -I<catch2包>/include \
  consumer.cpp <catch2包>/lib/libCatch2Main.a <catch2包>/lib/libCatch2.a -pthread -o consumer
```

## 参考

- [源码仓库](https://github.com/rollbear/trompeloeil)
- [文档](https://github.com/rollbear/trompeloeil/blob/main/docs/reference.md)
- [Boost Software License 1.0](https://www.boost.org/LICENSE_1_0.txt)
