# GNOME 0.84 线 C++23 代码在 OHOS clang 15 上的四类回退

## 错误特征

面向 C++23 的上游代码在 OHOS SDK clang 15 上报四类错误之一：

```
error: invalid value 'gnu++23' in '-std=gnu++23'          # 拼写不识别
expected '>' after 'typename' / use of undeclared ident    # P0634 隐式 typename
error: no member named 'out_ptr' in namespace 'std'        # P1132 C++23 库特性
error: no member named 'make_unique_for_overwrite'         # P0980 C++20 库特性
```

## 根因

| 上游用法 | 标准化 | clang 15 现状 |
|---|---|---|
| `-std=gnu++23` | C++23 | 15 只认 provisional 别名 `gnu++2b`（16 才认 23 拼写） |
| 隐式 typename（依赖类型名省略 typename） | P0634（C++20） | clang 16 才完成实现 |
| `std::out_ptr` / `std::inout_ptr` | P1132（C++23） | libc++ 未实现 |
| `std::make_unique_for_overwrite` | P0980（C++20） | libc++ 缺失 |

## 解法（四连 patch，vte/0.84.1 实证）

1. **拼写别名**：`gnu++23` → `gnu++2b`（同一标准的两种拼写，零语义差异）。
2. **显式 typename**：按编译错误逐点补 `typename`（E397 的三模式定位法）。
3. **out_ptr 回退**：`std::out_ptr(p)` 智能指针互操作 → 裸指针 + `reset()`。
4. **make_unique_for_overwrite → make_unique**：仅当缓冲区随后被完整覆写
   （不读未初始化内存）时语义等价——patch 描述必须写明等价性依据
   （vte 的 fmt-glue.cc:34 缓冲区被 simdutf 转换全量覆写）。

## 红线

- 第 4 项不是无条件等价：若代码**读取**缓冲区未初始化内容（依赖 zero/未定义值），
  `make_unique`（值初始化）与 `make_unique_for_overwrite`（不初始化）行为可观测
  不同——必须核实使用点后再替换。
- 第 1 项是治标拼写：升级工具链后应回移 `gnu++23`。
