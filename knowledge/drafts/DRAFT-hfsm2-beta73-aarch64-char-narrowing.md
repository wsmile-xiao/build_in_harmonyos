# DRAFT — aarch64 上 plain-char 无符号导致上游 C++ 测试编译期窄化（-Wc++11-narrowing）

> 状态: 草稿（基于 hfsm2 Beta73 R01 真实证据，2026-09-05）。
> 查重: E419 部分覆盖；草稿/error-patterns 无命中 → 本条目为边界扩展。

## 真实问题（场景）

hfsm2 Beta73（header-only C++14 分层状态机，andrew-gresyk/HFSM2）上游测试套件
（Catch2 v2，`test/*.cpp` + `test/shared/*.cpp` → 单一 `hfsm2_test` 可执行）在
OHOS PC aarch64（clang 15.0.4, aarch64-unknown-linux-ohos）直接编译失败：

```
test/test_debug.cpp:230:4: error: constant expression evaluates to -2 which cannot be
narrowed to type 'char' [-Wc++11-narrowing]
```

共 5 处（-1/-2 负值 char 列表初始化），`clang++ -std=c++17 -I external -I include
test/main.cpp test/*.cpp test/shared/*.cpp` 编译 EXIT 1。

## 根因

aarch64 ABI 默认 `char` 为 **unsigned**（x86 默认为 signed）。上游测试源码按 x86
语义把 -1/-2 负值写入 char 列表初始化（如 debug 日志采样数组），C++11 列表初始化在
**编译期**即以窄化拒绝（`-Wc++11-narrowing`），尚未进入运行期。这与既有条目 E419
（C 语言 plain char 符号性导致运行时 INT8 API 结果差异 +256）是同一根因
（aarch64 char 符号性）的**编译期表现**。E419 聚焦 C 库运行时 API 结果，未描述
C++ 测试源码编译期窄化，也未覆盖 header-only 库的修复位。

关键区分：header-only 库**无编译产物**，无库工具链 cflags 可注入——修复只能落在
测试/验证构建命令（或测试 CMake target 的 compile options），这是与 E419
（"add -fsigned-char through the package toolchain"）的实质差异。

## 验证

| 命令 | 结果 |
|------|------|
| `clang++ -std=c++17 -I external -I include test/main.cpp test/*.cpp test/shared/*.cpp` | EXIT 1，5 处 -Wc++11-narrowing |
| `clang++ -std=c++17 -fsigned-char -I external -I include test/*.cpp test/shared/*.cpp -o hfsm2_test` | EXIT 0 |
| `./hfsm2_test` | `All tests passed (35691 assertions in 17 test cases)` EXIT 0 |
| `./hfsm2_test --list-tests` | 17 项注册 |

日志: `.atomcode/oh-executor/logs/hfsm2-Beta73/upstream_compile_baseline.log`（失败）、
`upstream_compile_signedchar.log`（成功）。

## 适用范围

- 所有在 aarch64/OHOS 上编译的上游 C/C++ 测试套件，测试源码含负值 char 列表初始化
  （调试/图像/序列化采样数组）；尤其 header-only 库的验证构建。
- 跨库可复用：同族库（其他 header-only C++14+ 状态机/事件库）及任何
  上游 GLOB 测试 + 单可执行 + Catch2/GTest 的库。

## 适用边界 / 反例

- **不适用**：测试源码无负值 char 窄化、或目标 char 已有显式 signed/unsigned 的用例。
- **反例**：把期望值从 -2 改写为 254 或测试内强转 `static_cast<char>`——掩盖语义，
  上游测试并未通过原期望验证（E419 forbid 同族）。
- 与 E419 的边界：E419 = 运行时结果差异（编译已过）；本条目 = 编译期窄化失败。
  前者注入库工具链 cflags，后者注入测试构建标志。

## 关系

- similar_to: E419（consistent-target-signed-char-mode）
- caused_by: aarch64 plain-char 默认 unsigned（与 E419 同根因）
- prerequisite_of: 无
- conflicts_with: 无

## 决定

`new_draft` — 与 DRAFT-hfsm2-beta73-uppercase-tag-version-slug 同 PR 入库。