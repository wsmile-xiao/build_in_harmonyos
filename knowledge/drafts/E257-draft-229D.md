# E257 — C++20 typename elision (P0634R3) not supported by clang 15

## 错误特征
```
error: missing 'typename' prior to dependent type name 'X<...>::type'
error: expected a type  (for Y::template Z<...> patterns)
```
编译器报告所有使用 `X<...>::type`、`Y::template Z` 等依赖类型名时缺少 `typename` 关键字。

## 触发条件
- 构建系统: cmake (任意 C++ 构建)
- 阶段: compilation
- 编译器: clang 15.0.4 (OHOS SDK)
- C++ 标准: C++20 (-std=c++20)

## 根因分析
entt v4.0.0 使用 C++20 P0634R3 特性（在依赖类型名前省略 `typename` 关键字），但 OHOS SDK 中的 clang 15.0.4 对此特性支持不完整。P0634R3 在 clang 16+ 中才完全实现。这导致编译器在所有省略 `typename` 的依赖类型名处报错。

## 解决方案

### 推荐方案
在所有依赖类型名前添加 `typename` 关键字。三种模式：
1. `using X = Y<...>::type;` → `using X = typename Y<...>::type;`
2. `using X = Y::template Z<...>;` → `using X = typename Y::template Z<...>;`
3. `using X = alloc_traits::member;` → `using X = typename alloc_traits::member;`

使用 clang `-ferror-limit=0` 输出解析所有错误位置，批量插入 `typename`。

### 禁止做法
- ❌ 降级到 C++17（entt v4.0.0 需要 C++20 特性如 concepts、ranges）
- ❌ 仅修复部分文件（错误会级联到其他头文件）

## 验证
```bash
clang++ -std=c++20 -I src test.cpp -o test && ./test
```
编译通过且测试程序运行返回 0 即修复成功。

## 影响范围
- entt v4.0.0: 32 个头文件，158 处插入
- 通用: 任何使用 P0634R3 typename elision 的 C++20 库在 clang < 16 上编译
