# Lager

## 简介

Lager 是一个 C++ 库，用于实现值导向设计（value-oriented design），通过 Lenses 和 Observers 提供响应式状态管理能力，类似于 Redux 在 JavaScript 生态中的应用。

## 功能概述

- **不可变数据结构访问**：通过 Lenses 提供对不可变数据结构的简洁访问和修改接口
- **响应式状态管理**：基于 Observers 模式，实现状态的订阅和更新通知
- **时间旅行调试**：支持状态快照和历史回溯，便于调试复杂状态变化
- **Redux 风格架构**：提供 Action、Reducer、Store 等概念，便于构建可预测的状态管理流程
- **类型安全**：利用 C++ 模板系统，提供编译期类型检查
- **Header-only**：无需编译库本身，只需包含头文件即可使用

## OHOS 适配

### 适配要点

1. **Header-only 库**：Lager 是 header-only 库，无需单独编译，直接集成到项目中即可
2. **C++17 要求**：需要支持 C++17 或更高版本的编译器（clang++）
3. **依赖管理**：
   - 核心依赖：range-v3（范围库）
   - 可选依赖：zug（依赖注入库）
4. **无平台特定代码**：纯 C++ 模板库，不依赖操作系统特性，适配简单

### 已知问题

- 当前版本 0.1.1 已成功编译验证，状态为 `built`
- 未发布预编译包（header-only 库通常不需要）

### 与 Linux 的差异

无显著差异，作为 header-only 库在 OHOS 和 Linux 上使用方式完全一致。

## 依赖

### 编译依赖

- **range-v3**：C++ 范围库，提供现代 C++ 的范围操作
- **zug**（可选）：依赖注入和函数式编程工具

### 运行依赖

- C++17 运行时库

## 安装方法

### 从源码集成

```bash
# 克隆仓库
git clone https://github.com/arximboldi/lager.git

# 在 CMake 项目中集成
add_subdirectory(lager)
target_link_libraries(your_target PRIVATE lager)
```

### Header-only 集成

```cpp
// 直接包含头文件
#include <lager/lenses.hpp>
#include <lager/watch.hpp>
#include <lager/store.hpp>
```

## 使用示例

### 简单状态管理

```cpp
#include <lager/store.hpp>
#include <lager/reducer.hpp>
#include <iostream>

// 定义状态类型
struct counter_state {
    int value = 0;
};

// 定义 Action
struct increment {};
struct decrement {};

// 定义 Reducer
auto reducer = lager::make_reducer(
    [](counter_state state, increment) {
        state.value++;
        return state;
    },
    [](counter_state state, decrement) {
        state.value--;
        return state;
    }
);

// 创建 Store 并使用
int main() {
    auto store = lager::make_store<counter_state>(reducer);

    store.dispatch(increment{});
    std::cout << "Counter: " << store.get().value << std::endl;  // 输出: 1

    return 0;
}
```

### 使用 Lenses 访问嵌套状态

```cpp
#include <lager/lenses.hpp>
#include <zug/transducer/filter.hpp>

struct user {
    std::string name;
    int age;
};

// 使用 lens 访问嵌套字段
auto name_lens = lager::lens(
    [](const user& u) { return u.name; },
    [](user u, std::string name) { u.name = name; return u; }
);
```

## 功能验证

Header-only 库功能验证通过编译测试：

```bash
# 验证头文件完整性
ls /path/to/lager/include/lager/
# 应包含核心头文件：lenses.hpp, watch.hpp, store.hpp 等
```

## 参考资料

- **GitHub 仓库**：https://github.com/arximboldi/lager
- **文档**：https://sinusoid.es/lager/
- **示例代码**：https://github.com/arximboldi/lager/tree/master/example