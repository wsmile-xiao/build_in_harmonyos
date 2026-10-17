# fatal

Facebook Template Library（fatal）——Facebook 开源的 **header-only C++ 模板元编程库**。
它把 C++ 模板元编程里最啰嗦的部分（类型列表、变换、查找、反射、编译期算术等）
封装成易用接口，让普通业务代码也能直接享受元编程的表达力；同时附带 `lesson/`
教程与 `demo/` 示例。

- 上游仓库：https://github.com/facebook/fatal
- 官网/讨论组：https://www.facebook.com/groups/libfatal/
- 许可证：BSD-3-Clause（附专利授权 PATENTS）

## 功能概述

| 模块 | 内容 |
|------|------|
| `fatal/type/` | 类型列表（`list`）、变换、过滤/查找、排序、反射（函数/成员函数/模板）、枚举、Trie、注册表、编译期算术 |
| `fatal/container/` | `variant`、`optional`、`flag_set`、`static_array`、`circular_queue`、`variadic_union` 等 |
| `fatal/string/` | `rope`（分段字符串 + 双向迭代器）、`string_view`、`tokenizer` |
| `fatal/codec/` | `varint` 编解码 |
| `fatal/math/` | 编译期 RNG、数值、统计矩、hash |
| `fatal/portability.h` | 编译器/平台差异封装（含 MSVC 兼容层） |
| `fatal/test/` | 自带单元测试驱动（`FATAL_TEST` / `FATAL_EXPECT_*`），仅用于测试 |

## OHOS 适配

**适配类型：header-only（无编译产物）**，`conanfile.py` 只做两件事：安装
`fatal/` 头文件树，执行上游官方测试套件。

要点：

1. **上游用例全量实跑**：上游自带 `test.sh`/`compile.sh` harness，本包在
   `build()` 中逐字复刻其编译参数（`-O0 -g -pthread -ftemplate-depth-1024
   -Wall -Werror -Wextra -std=c++17`）逐个编译并运行 67 个 `*_test.cpp`
   （839 个可执行 `FATAL_TEST` 用例），实测 **839/839 = 100% 通过**。
2. **`/tmp` 只读**：鸿蒙 PC 的 `/tmp` 是只读 erofs，上游 `compile.sh` 固定往
   `/tmp/.build` 写中间产物，因此配方不复用该脚本，直接编译到 Conan 构建目录。
3. **工具链严格化补丁**（2 个，均为 portability）：
   - `rope.h` 的 `const_iterator` 去掉 C++17 已弃用的 `std::iterator` 基类
     （libc++ 标了 `deprecated`，`-Werror` 下编译失败）；
   - 测试中 `std::tuple_element<2, std::pair>` 的「不完整类型」断言加
     `#if !defined(_LIBCPP_VERSION)` 守卫（新版 libc++ 对越界索引有
     `static_assert`，实例化即硬错误）。
4. **无外部依赖**：不依赖任何第三方库，消费者只需 include 路径。

已知限制：

- 6 个上游 `FATAL_TEST` 桩位于 `rope_test.cpp` 的 `/* TODO: IMPLEMENT */`
  块注释内（上游未实现、未编译），本包亦不修改上游这一状态。
- `fatal/` 中 `deprecated/` 子树（如 `type/deprecated/transform.h`）为上游
  遗留 API，保留但不建议新代码使用。

## 依赖关系

- 编译依赖：无
- 运行依赖：无

## 版本

| 版本 | 上游 tag | 状态 | 说明 |
|------|----------|------|------|
| v2026.09.14.00 | v2026.09.14.00 | built | 上游 839/839 用例通过 + 3 个消费者用例 |

## 参考资料

- 上游 README：https://github.com/facebook/fatal/blob/main/README.md
- 教程（learn-by-example）：https://github.com/facebook/fatal/tree/main/lesson
- 示例：https://github.com/facebook/fatal/tree/main/demo
- CppCon 2014 演讲：https://www.youtube.com/watch?v=0A9pYr8wevk
