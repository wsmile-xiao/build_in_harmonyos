# C++17 移除 std::bind2nd 仿函数适配器

> DRAFT-coinor-vol-1.5.4-std-bind2nd-removed-cpp17（知识库扩展草稿，路径 B）
> 与 coinor-vol 1.5.4 归档同 PR 交付（PR #8922 R03 批次）。

## 问题

启用上游测试（`COIN_HAS_OSITESTS=1`，R03 配方接入 Osi/CoinUtils 依赖）后，
OsiVol 接口层在 clang `-std=c++17` 下编译失败：

```text
OsiVolSolverInterface.cpp:471:9: error: no member named 'bind2nd' in namespace 'std'
```

`std::bind2nd`（以及 `std::bind1st`/`ptr_fun`/`mem_fun` 等旧仿函数适配器）
C++11 标记 deprecated、C++17 正式移除。2003 年代 C++ 代码
`std::transform(... std::bind2nd(std::multiplies<double>(), objsense_))`
在 OHOS 固定 cppstd=17 的 profile 下无法编译。

## 根因

- 上游 2003 年代代码使用 `std::bind2nd` 将二元仿函数绑定为一元操作符
- OHOS profile 固定 `compiler.cppstd=17`，`bind2nd` 已移除 → 硬错误
- 与 E293（register 关键字移除）同族：均为旧代码在 C++17 下的特性移除

## 方案（最小补丁）

用 lambda 替换（语法最简、无新增 include 需求）：

```cpp
// 前：std::bind2nd(std::multiplies<double>(), objsense_)
// 后：[this](double v) { return v * objsense_; }
std::transform(rowprice_, rowprice_+dsize, dsol.v,
               [this](double v) { return v * objsense_; });
```

⚠️ lambda 捕获陷阱：**成员函数内访问成员变量时必须显式 `[this]`**；
直接写 `[objsense_]`（成员变量名）会报两级错误
`'objsense_' in capture list does not name a variable` 与
`'this' cannot be implicitly captured in this context`。

## 验证

- 替换后 `make -j1`（含 OsiVol 接口层）rc=0，libOsiVol.a 构建成功
- `make -j1 -C Vol/test osiUnitTest` rc=0，osiUnitTest 二进制产出
- 完整 conan create（R03 配方）rc=0，test_package 1/1 Passed
- 上游 3 个用例实跑 3/3 (100%)（日志 SHA-256
  `9ac3de069cfa1b7133762c833646e0965c29361baf0e1034c0cb28a5acd7b42c`）

## 适用边界与反例

- 适用：2003 年代 C++ 库在 cppstd=17 下使用 bind1st/bind2nd/ptr_fun/mem_fun 的
  任何代码（含被安装头文件与接口层），跨库可复用
- 反例：C++11 及以上代码（标准库已无这些适配器，不会出现该错误）
- 与 E293 关系：同族但不同物——register 是语言关键字移除（-Wno-error 可降级为
  警告的库内部场景例外），bind2nd 是标准库 API 移除且 C++17 下为硬错误，
  无 toolchain-flag 兜底；均须源码补丁

## 关系

- similar_to: E293（C++17 旧特性移除，源码补丁）
- caused_by: C++17 标准库移除 bind2nd
- 查重决定：`new_draft`（知识库无 bind2nd 条目，验证充分、可跨库复用）