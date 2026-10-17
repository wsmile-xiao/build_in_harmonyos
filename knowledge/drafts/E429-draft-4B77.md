# E429 — OHOS libc++ 15.0.4 缺 <memory_resource>：std::pmr 编译失败，强用 experimental 运行期 SIGSEGV

## 错误特征
- 编译期：`fatal error: 'memory_resource' file not found`（`#include <memory_resource>`）
- 强走 experimental 路径后：broker 13 个单测运行期 SIGSEGV（引用 `experimental::pmr::get_default_resource()` 符号缺失）

## 触发条件
- 平台/工具链: OHOS SDK clang 15.0.4，libcxx-ohos（_LIBCPP_VERSION 15004）
- 阶段: compilation | linking | runtime
- 典型代码: 使用 std::pmr（polymorphic_allocator / monotonic_buffer_resource 等）的 C++17/20 软件；zeek 8.2.1 auxil/broker 实测 37 处使用

## 根因分析
SDK 的 libcxx-ohos 不带 C++17 标准 `<memory_resource>` 头，只有 `<experimental/memory_resource>`；
且该 experimental 头对 monotonic_buffer_resource / 全局资源函数**只声明未定义**（SDK libc 不导出符号）。
两条死路：标准头直接编译失败；强用 experimental 则 default-constructed polymorphic_allocator
运行期引用缺失符号 → SIGSEGV。

## 解决方案

### 推荐方案（shim 头 backport）
自写 shim 头 `<memory_resource>` 经 -I 注入 include 路径最前，不改上游源码：
1. 复用 SDK experimental 头的真实基类
2. 自实现正确 bump-pointer monotonic_buffer_resource（每次分配必须对齐，否则内存破坏）
3. inline 定义 new_delete_resource / get_default_resource / set_default_resource / null_memory_resource
4. 补 `experimental::pmr::get_default_resource()` 转发符号（命名空间对齐，否则运行期仍悬空）

修复后 13 个曾 SEGFAULT 的 broker 测试 100% 恢复。

### 禁止做法
- ❌ 仅 `#include <experimental/memory_resource>` + using-namespace 桥接 → monotonic buffer 与全局资源缺定义，运行期 SIGSEGV

## 验证
```bash
find <sdk>/include/c++/v1 -name memory_resource       # 无标准头 = 命中
llvm-nm -D <sdk libc.so> | grep get_default_resource  # Not found = 命中
cmake -S . -B build -DCMAKE_CXX_FLAGS="-I${OHOS_SHIM_DIR}" && ctest -R broker   # 13 个 SEGFAULT 项应全过
```

## 关联条目
- 同来源: PR #11976（zeek 8.2.1，auxil/broker）
