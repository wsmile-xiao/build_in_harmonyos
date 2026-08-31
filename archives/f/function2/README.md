# function2

## 软件描述

function2 是一个 header-only 的 C++ 库，提供对 `std::function` 的增强替代实现：

- `fu2::function` — 可拷贝的函数包装器（含 `const`/`volatile`/`reference`/`noexcept` 限定）
- `fu2::unique_function` — 仅可移动的函数包装器（可持有 move-only 对象）
- `fu2::function_view` — 非拥有的函数视图

## 主要功能

- 支持 move-only 类型的调用对象
- 支持任意数量签名重载（模板列表形式）
- 通过 `fu2::function_base` 可配置内部容量、可拷贝性与异常保证
- 与 `std::function` 可相互转换
- 单头文件 `include/function2/function2.hpp`，仅依赖标准库
- Boost Software License 1.0

## 使用示例

```cpp
#include "function2/function2.hpp"
fu2::function<int(int)> f = [](int x) { return x * 2; };
int r = f(21);  // r == 42
```

## 版本信息

- 最新版本：4.2.3（2023-07-13）
- 官方仓库：https://github.com/Naios/function2
- 官方文档：http://naios.github.io/function2/

## 鸿蒙适配状态

| 项目 | 状态 | 说明 |
|------|------|------|
| 源码核验 | ✅ 完成 | tag 4.2.3 = commit 9e303865d14f1204f09379e37bbeb30c4375139a，tarball sha256 已核验 |
| 配方骨架 | ✅ 已建立 | conanfile.py + conandata.yml + test_package 骨架就绪 |
| 编译验证 | ⏳ 待执行 | 首轮 Adapt 本地验证阶段执行 |

## 相关链接

- [官方仓库](https://github.com/Naios/function2)
- [官方文档](https://naios.github.io/function2/)