# E585 — OHOS libc++ 无 `<tr1/memory>`：TR1 写法需迁移到 C++11 标准库

## 错误特征

```
fatal error: 'tr1/memory' file not found
#include <tr1/memory>
         ^~~~~~~~~~~~
1 error generated.
```

- 编译工具：clang（OHOS PC 工具链，LLVM libc++）
- 报错位置：仍使用 `#include <tr1/memory>` 的旧版 C++ 代码（C++11 之前 TR1 写法）
- 典型扩展错误：`std::tr1::shared_ptr`、`std::tr1::enable_shared_from_this` 均不可用

## 触发条件

- **构建系统**：任意（CMake/Autotools/Makefile 均可能）
- **阶段**：compilation（编译任何包含该头的翻译单元时）
- **平台**：OHOS（HarmonyOS PC）工具链——LLVM libc++ 不提供 `tr1/` 目录下的兼容头；旧 Linux 发行版（glibc libstdc++ ≤ C++11 时代浏览器）才有

## 根因分析

OHOS 工具链的 libc++（LLVM 实现）不提供 C++ TR1（Technical Report 1）兼容头文件。`<tr1/memory>` 属于 C++03/TR1 时代的过渡标准库写法，标准库从 C++11 起就把 `shared_ptr` / `enable_shared_from_this` 等并入 `std::` 命名空间并置于 `<memory>`。仍在头文件中写 `#include <tr1/memory>` 并用 `std::tr1::shared_ptr` 的旧代码，在 clang + libc++ 下无法编译。

这与 E127（pthread_cancel 缺失）类似，属于消息头格式：libc++ 比 libstdc++ 更早移除了 TR1 兼容层——libstdc++ 通常通过 `std::tr1` 别名继续提供，libc++ 直接不提供。

## 解决方案

### 推荐方案：迁移到 C++11 标准库

将 `#include <tr1/memory>` 改为 `#include <memory>`，并将 `std::tr1::shared_ptr` / `std::tr1::enable_shared_from_this` 改为 `std::shared_ptr` / `std::enable_shared_from_this`（C++11 标准库已内置，无需额外依赖链接）：

```bash
sed -i 's|#include <tr1/memory>|#include <memory>|; s|std::tr1::shared_ptr|std::shared_ptr|g; s|std::tr1::enable_shared_from_this|std::enable_shared_from_this|g' include/shared_ptr.hpp
```

vzlogger 0.8.9 实证：`include/shared_ptr.hpp` 迁移后编译通过（apriori）。grep 确认无 `std::tr1` 残留。

### 回退方案：自研转发头（仅临时）

若 TR1 用法遍布多处、迁移影响面过大，可提供 `<tr1/memory>` 转发头（`#include <memory>` + `using std::shared_ptr` 到 `std::tr1` 命名空间），但仅建议临时过渡，最终仍应迁移。注意 Avoid ABI 冲突：不要同时定义与 `std::` 同名的非标准实体。

### 禁止做法

- ❌ 为 `<tr1/memory>` 写空 stub 头（`#ifndef` 空壳）——头文件缺失是"不存在"而非"符号冲突"，stub 无意义且引入 `std::tr1` 与 `std::` 双命名空间歧义风险
- ❌ 用 `-I` 指向别的兼容头目录绕路（若上游存在 tr1 目录则可用，但 OHOS libc++ 本身没有）

## 验证

```bash
# 1) 定位所有 TR1 引用
grep -rn "tr1/memory\|std::tr1" --include="*.h" --include="*.hpp" --include="*.cpp" <src_dir>

# 2) 修复后重新编译确认
make -j"$(nproc)" 2>&1 | grep -E "tr1|error" || echo "OK: 无 tr1 错误"
```

vzlogger 0.8.9 实测：迁移后 `make -j2` 全部 target 构建成功，无 tr1/memory 报错。

## 关联条目

- 相关：E127（OHOS pthread_cancel 缺失——同为 OHOS libc 与 Linux 差异）