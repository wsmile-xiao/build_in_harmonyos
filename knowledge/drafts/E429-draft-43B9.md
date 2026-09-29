# E429 — C++17 迁移旧 C++ 静态库 auto_ptr→unique_ptr：拷贝语义所有权转移需补 std::move + Boost iterator_facade 限定调用改 ADL

> 草稿（DRAFT，contributor 43B9）。与同目录 `E429-draft-43B9.kv` 成对。
> 来源：luabind 0.9.1 适配（OHOS aarch64，feat/luabind-0.9.1），2026-09-28 实测。

## 错误特征

```
error: no member named 'auto_ptr' in namespace 'std'
        std::auto_ptr<T> instance(new T);
        ^
error: call to implicitly-deleted copy constructor of 'std::unique_ptr<detail::registration>'
        m_registration->m_members.operator,(scope(ptr));
error: no matching function for call to 'operator=='
      return boost::operator op(x, y);
```

三组错误同时出现在一个旧 C++ 库的 C++17 适配中：

1. **auto_ptr 移除**：`std::auto_ptr` 自 C++17 起被标准移除，公共头/源码直接引用即失败；
2. **unique_ptr 拷贝删除**：把 auto_ptr 全局替换为 unique_ptr 后，凡依赖 auto_ptr「拷贝即转移所有权」
   语义的按值持有/传参点（`pointer_holder` 成员、`make_instance`/`constructor` 的 `holder_type` 构造、
   `class_base::add_member` 的 `scope(ptr)` 值传递、`make_pointee_instance`）报 implicitly-deleted copy；
3. **Boost iterator_facade 限定调用失效**：`boost::operator==(x, y)` 在 Boost>=1.73 找不到匹配
   （运算符定义于 `boost::iterators` 命名空间，仅 `iterator_facade` 经 using 引入 boost）。

## 触发条件

- 构建系统: 无（bjam/Jamroot 上游）+ Conan 手动编译（src/*.cpp 直接 clang++）
- 消费者 profile: `compiler.cppstd=17`（OHOS 统一 cppstd=17）
- 依赖: lua/5.1.5 + boost/1.90.0（registry 已发布）

## 根因分析

OHOS 平台统一 `compiler.cppstd=17`；2010 年代旧 C++ 库的公共头把 `std::auto_ptr` 用作
「按值持有/传参的所有权转移」工具。`std::unique_ptr` 语义等价但**禁止拷贝**——auto_ptr 的
`copy` 即转移，unique_ptr 必须显式 `std::move`，因此简单 `s/auto_ptr/unique_ptr` 无法编译。
另外 Boost 1.90 的 `iterator_facade` 比较运算符迁移到 `boost::iterators` 命名空间（仅类名
经 using 引入 boost），旧代码 `boost::operator op(x, y)` 限定调用失效，需改 ADL 非限定 `x op y`。

## 推荐方案

1. 公共头+src 统一 `std::auto_ptr` → `std::unique_ptr`；
2. 对每一处 auto_ptr 拷贝转移语义的调用点补 `std::move`：
   - `make_instance.hpp`：`holder_type(std::move(p), ...)`；
   - `constructor.hpp`：`holder_type(std::move(ptr), ...)`；
   - `class.cpp`：`scope(std::move(ptr))`；
   - `policy.hpp`：`make_instance(L, std::move(x))` / `make_instance(L, std::move(ptr))`；
   - `instance_holder.hpp`：`p(std::move(p))`；
3. `object.hpp`：`boost::operator op(x, y)` → `x op y`（ADL）；
4. `has_get_pointer.hpp`：显式 `#include <boost/mpl/bool.hpp>`；
5. 全部固化到 `patches/0001-modern-boost-compat.patch`，conan create 复验。

## 验证

```bash
# src 全量 C++17 回归编译（0 error）
clang++ -c -O2 -fPIC -std=c++17 -I. -I<boost> -I<lua> src/*.cpp
# conan create 消费者 test_package（Greeter 绑定 + Lua 调用 count=2 通过）
conan create archives/l/luabind/0.9.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=default --build=missing
# 上游测试：44 个 SOURCES 用例中 39 个通过（5 个 rc=134 崩溃经隔离对照为上游/工具链既有问题，
# 原始源码同样复现，非本轮补丁回归）
```

## 适用边界与反例

- **适用**：公共头/源码以 std::auto_ptr 作为按值持有/传参所有权转移手段的旧 C++ **静态库**
  （可重编译、无 ABI 包袱），且消费者按 cppstd>=17 编译；依赖 Boost iterator_facade 且
  `boost::operator op()` 限定调用、升级 Boost>=1.73 后失效的旧 C++ 库。
- **反例**：公共头 auto_ptr 成员参与**数据布局/ABI**的库（此时布局不兼容，须用 bulletml 式
  内联布局兼容 shim + `__cplusplus` 宏选择，见 DRAFT-bulletml-0.0.6-auto_ptr-cpp17-compat）；
  header-only 库若仅删除抽象基类指针，注意补 virtual 析构（见
  DRAFT-igloo-1.1.1-cpp17-auto-ptr-unique-ptr-abstract-dtor）。
- **限制**：`std::move` 只能补在「所有权确实转移、调用后原对象不再使用」的位置；若调用后
  仍需使用原 unique_ptr，则需先拷贝语义设计（如 shared_ptr），不能机械补 move。

## 查重差异（七轴）

| 轴 | 结论 |
|---|---|
| exact_duplicate | false |
| causal_duplicate | false |
| trigger_overlap | true（bulletml/igloo 同为 auto_ptr C++17 移除） |
| solution_overlap | true（bulletml: shim；igloo: 直接替换；luabind: 直接替换 + 拷贝语义 std::move 清单） |
| combination_novelty | true（静态库拷贝语义迁移的具体 std::move 点位清单 + Boost iterator_facade 限定调用 ADL 修复） |
| boundary_novelty | true（区分静态库可重编译直迁 vs 有 ABI 约束用 shim 的边界） |
| test_migration_novelty | true（44 上游用例 5 个崩溃经隔离对照定性为上游/工具链既有问题） |

关系：`similar_to` = DRAFT-bulletml-0.0.6-auto_ptr-cpp17-compat, DRAFT-igloo-1.1.1-cpp17-auto-ptr-unique-ptr-abstract-dtor, E293。
