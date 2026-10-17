# E433 — 旧 libc++ std::construct_at 不支持聚合体初始化

## 错误特征
- `no matching function for call to 'construct_at'`
- 典型: 聚合 struct 的 `vector::emplace_back(...)` 失败

## 触发条件
- 平台/工具链: OHOS SDK clang 15.0.4，libc++ 15.0.4
- 阶段: compilation
- 典型代码: C++20 代码中把含指针/引用成员的聚合 struct（无用户声明构造函数）emplace_back 进容器；
  zeek 8.2.1 实测 CallInfo（const CallExpr*/Frame* 聚合 struct）与 script_opt 的 DispatchInfo

## 根因分析
OHOS SDK libc++ 15.0.4 的 std::construct_at 实现未覆盖聚合体括号初始化路径（新版 libc++ 已支持）。

## 解决方案

### 推荐方案
给聚合 struct 补 constexpr（或普通）构造函数——可移植，新旧 libc++ 皆可。
zeek 的 CallInfo 与 DispatchInfo 两处均一次修复。

## 验证
```bash
# 最小探针: struct A 含 const void* 成员后 vector::emplace_back(nullptr)
clang++ -std=c++20 -c probe.cc   # 旧 libc++ 报 no matching function = 命中
make                              # 相关目标编译通过 = 修复验证
```

## 关联条目
- 同来源: PR #11976（zeek 8.2.1）
