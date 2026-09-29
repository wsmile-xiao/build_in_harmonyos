# E430 — OHOS libc++ 15.0.4 的 <ranges> 头存在但算法成员整批缺失

## 错误特征
- `no member named 'sort' in namespace 'std::ranges'`（同类：find/copy/transform/unique/remove 等全部 no member）
- 经模板（.pac/.bif 生成的 Dict.h/telemetry 源码链）间接命中时，错误信息指向无关文件

## 触发条件
- 平台/工具链: OHOS SDK clang 15.0.4，libcxx-ohos
- 阶段: compilation
- 典型代码: 使用 std::ranges 算法的 C++20 软件；zeek 8.2.1 实测 47 文件 83+ 使用点

## 根因分析
SDK 的 libcxx-ohos 中 `<ranges>` 头存在，但 `__cpp_lib_ranges` 未定义，std::ranges 命名空间的
算法集（sort/find/copy/transform/unique/remove 等）**整批缺失——命名空间在、算法不在**，
属硬平台约束（-stdlib=libc++ 单独探针同样编不过）。

## 解决方案

### 推荐方案（机械映射改写为经典 STL）
- `std::ranges::sort(v,cmp)` → `std::sort(v.begin(), v.end(), cmp)`
- `reverse_view` → 反向迭代器
- `ranges::unique`（返回对）→ `std::unique`（单迭代器）
- `ranges::remove` + `begin`（erase-remove 惯用法）→ `v.erase(std::remove(...), v.end())`

**派生陷阱（zeek 实测）**：机械改写时把原始 C 数组当容器用 `.begin()/.end()` 会再报
member reference base type 错误——C 数组须用 `std::begin/std::end`。
改写后须全树 `grep std::ranges::` 清零 + C 数组调用点专项复查。

### 禁止做法
- ❌ 保留 std::ranges 调用改试其他编译选项 → 平台硬约束，单独探针已证伪

## 验证
```bash
clang -E -dM -x c++ - | grep __cpp_lib_ranges   # 未定义 = 命中
grep -rn 'std::ranges::' src/ auxil/ | wc -l    # 改写后应为 0
```

## 关联条目
- 同来源: PR #11976（zeek 8.2.1）
