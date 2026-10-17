# E1003 — 单头文件 C++ 库缺 `<system_error>` 包含：OHOS libc++ 无传递包含致消费者编译失败（上游 doctest include 顺序掩盖）

## 错误特征
```
clang-15: error: no member named 'system_error' in namespace 'std'
            throw std::system_error(errno, std::system_category());
                  ~~~~~^
clang-15: error: no member named 'system_category' in namespace 'std'
```
仅当消费者源文件**只包含该公开头**（如仅 `#include <lazycsv.hpp>`）时出现；
同一头文件被上游测试源（先 `#include <doctest.h>`）编译时无此错误。

## 触发条件
- 构建系统: 任意（本证据为 cmake/直接 clang++ 编译）
- 阶段: compilation
- 环境: HarmonyOS PC arm64，OHOS 适配版 libc++（`compiler.libcxx=libc++`，clang 15）

## 根因分析
源码头文件使用了 `std::system_error` / `std::system_category()`（如 mmap 封装抛错路径），
却未显式 `#include <system_error>`。linux libstdc++ 下 `<string>`/`<stdexcept>` 会传递包含
`<system_error>` 使编译"恰好通过"；OHOS 裁剪 libc++ 无此传递包含。上游 doctest 测试源因
先包含 `doctest.h`（内部含 `<system_error>`）把缺陷掩盖，导致缺陷只在 **消费者视角**暴露——
这与"consumer 用例必须独立于上游测试"的门禁设计互为印证：无消费者用例的上游 14/14 全绿
并不能发现头文件不自包含。

## 解决方案

### 推荐方案
在头文件 include 区显式加入 `#include <system_error>`（建议紧随 `<string_view>` 之后），
以 conandata patches（`patches: {version: [{patch_file, strip}]}`，conan 经 patch_ng 应用）
或源码最小补丁方式落地。修复后消费者编译通过；上游测试复跑无回归。

### 禁止做法
- ❌ 不用隐藏编译器开关（-fno-*）或 GNU 私有头（`<bits/...>`）绕过
- ❌ 不修改消费者用例来迁就头文件缺陷

## 验证
```bash
# 补丁前（OHOS，仅含公开头）必然复现首错；补丁后：
/data/service/hnp/bin/clang++ -std=c++17 -Wall -Wextra -Werror -I include -x c++ -fsyntax-only consumer.cpp
# 上游测试复跑（doctest）：test cases: 14 | 14 passed | 0 failed
```

## 关联条目
- similar_to: E455（OHOS clang 拒 -stdlib=libstdc++，同为 libc++/工具链系）、
  DRAFT-stdex-header-wrapper-shadow-std-headers（stdex 包装头劫持标准头，同属头文件与 libc++
  交互但触发不同）
- 真题佐证: lazycsv 3.8 R02（archives/l/lazycsv/3.8，patches/0001-system-error-include.patch）