# DRAFT-stdex-0.2.9-header-wrapper-shadow-std-headers

> 草稿状态：DRAFT — 待审核 promote 为正式 E 条目
> 来源事件：stdex 0.2.9 适配（task stdex-0.2.9-r01-bootstrap-and-adapt-pc1-37-20260905T123706Z）
> 作者：pc1-37

## 问题

stdex 0.2.9 的 `include/` 目录同时包含**无扩展名包装头**（`chrono`、`mutex`、`thread`、`type_traits`、`algorithm`、`iterator`、`cstdint`、`ratio`、`sstream`、`string`、`system_error`、`condition_variable`、`typeindex` 等，内容仅一行 `#include "xxx.hpp"`）与真正的 `.hpp` 实现头。

若把整个 `include/` 目录加入编译 `-I`：

```cpp
// 消费者
#include <type_traits>   // 被解析为 stdex 的 type_traits 包装头 → C++98 残缺实现
```

随后 libc++ 内部头（如 `<typeinfo>` → `<exception>`）直接编译失败：

```
/data/.../libcxx-ohos/include/c++/v1/exception:290:22: error: no template named 'decay'
    typedef typename decay<_Tp>::type _Up;
                     ^
```

## 根因

- stdex 是无构建系统的 C++98 时代库，为兼容旧编译器在 include/ 下放置与标准库同名的无扩展名包装头。
- 这些包装头把 `std` 命名空间的真实内容让位给 stdex 自己的 `stdex` 命名空间实现；但 `-I` 目录平铺后，`<type_traits>` 等标准头引用被劫持。
- libc++ 标准库头自身依赖 `std::decay`、`std::is_copy_constructible`、`std::nullptr_t` 等 C++11 特性；拿到 stdex 的 C++98 残缺实现后二次报错。
- 源文件内部使用相对包含（`#include "../include/thread.hpp"`），不受 `-I` 影响，因此仅打包/消费侧出错。

## 方案

1. **打包隔离**：conanfile.py `package()` 将库头安装到包内 `include/stdex/` 子目录；`package_info().includedirs=["include"]`。消费方使用 `#include <stdex/thread.hpp>`，不产生遮蔽。
2. **构建隔离**：构建库自身时不给编译命令加 `-I` 到包装头目录，依赖源文件相对 include。
3. **标准版本**：libc++ 头需要 C++11+，按 E130（`change-cxx-standard`）处理——使用 profile `compiler.cppstd=17` 编译（`-std=c++98` 直接失败，见 E130 同源签名）。

## 验证

| 步骤 | 命令 | 结果 |
|------|------|------|
| R01 反证 | `clang++ -std=c++17 -I stdex/include -c src/chrono.cpp` | ❌ libc++ `std::decay` 报错 |
| R01 修复 | `clang++ -std=c++17 -c src/chrono.cpp`（相对 include） | ✅ rc=0（仅 stdcall/fastcall 无害警告） |
| R01 修复 | 同法编译 mutex.cpp / thread.cpp | ✅ rc=0 |
| R02 配方 | `ohc-run.py conan-verify stdex 0.2.9` | ✅ G0-G4 + L2/L4/L5 全 PASS |
| R02 消费者 | test_package：stdex::thread 双线程 + stdex::mutex 计数器 | ✅ PASS（counter=200） |

日志（含 SHA-256，见 `.ci-result.json` log_sha256=dd5934c8...）：
- `archives/s/stdex/0.2.9/reports/conan-create.log`
- `archives/s/stdex/0.2.9/reports/conan-verify-report.md`
- `archives/s/stdex/0.2.9/reports/w3-local-ci.log`
- `archives/s/stdex/0.2.9/reports/test-report.md`

## 适用边界

适用于任何**自带与标准库同名且无扩展名包装头**、头目录可能被整体 `-I` 或平铺安装的库（stdex 及部分 C++98 时代兼容库）；也适用于头布局为源相对 include（`../include/`）的轻量库。

## 反例

- 头文件全部 `.h/.hpp` 后缀命名且不与标准库同名 → 平铺安装无遮蔽，无需子目录。
- header-only 且内部只用相对包含、消费方按子目录引用 → 可直接平铺。

## 关联

- 等价命中（路径 A）：候选 B「OHOS libc++ 需 C++17+」→ **E130** `change-cxx-standard`（正式条目，本轮逐字段验证适用：error_signature 同源 nullptr_t/decay 域、根因同为 libcxx-ohos 头要求、方案同为提标准到 cppstd=17）。无需新草稿。
- E217 / DRAFT-concurrencpp（CMake 安装子目录 vs includedirs 不匹配）：方向相反（消费方找不到头 vs 本条目遮蔽标准头），不构成等价。
- E133（musl 头遮蔽）：同为 -I 遮蔽域但机制不同（系统头 vs 库自带包装头）。
- E481：llvm-ar 工具链注入（meson 场景），已覆盖本库 llvm-ar 用法一部分。