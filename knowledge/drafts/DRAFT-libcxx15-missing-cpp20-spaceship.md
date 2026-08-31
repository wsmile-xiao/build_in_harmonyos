# DRAFT-libcxx15-missing-cpp20-spaceship：OHOS clang15/libc++15 缺 C++20 三路比较 operator<=>

> Contributor: sea_crab | Status: Draft | Updated: 2026-08-29
> Source: bali-phy 4.1 HarmonyOS PC adaptation（patch 0002）
> 对应：knowledge/drafts/DRAFT-libcxx15-missing-cpp20-spaceship.kv

## 现象

OHOS SDK clang 15.0.4（libc++，LLVM 15）下以 `-std=c++20` 编译 BAli-Phy 4.1，
凡对 `std::string` / `std::vector` / `std::variant` 直接使用 `operator<=>` 的位置
全部编译失败：

```text
no match for 'operator<=>'  (std::string / std::vector / std::variant)
```

上游 libc++ 状态表（llvm-project `libcxx/docs/Status/Cxx20Papers.csv`）将
P1614R2 "Library Support for the Spaceship Operator" 标为 |Complete| 且首发版本
= LLVM 19；OHOS SDK 15 的 libc++ 未含这些容器的 `<=>`，属 toolchain 能力缺口而非
源码错误。另一个隐蔽点：C++20 中 `defaulted operator<=>` 会隐含生成
`operator==`；一旦把 defaulted 改成手写等价，隐含 `operator==` 随之消失，必须
显式补回，否则引用 `==` 的编译点（如 `std::sort`/`map` 键比较）继续报错。

## 与现有知识的关系（确认去重证据）

检查范围：knowledge/graph + knowledge/drafts（本分支 HEAD 423 文件）+ 经验仓
ophs_ci_review（HEAD=1715154b，工作树干净）。
检索词：spaceship / operator<=> / three-way / strong_ordering / lexicograph /
libc++ / libcxx / c++20 / cpp20 / std::string / std::vector / std::variant。
graph 面 0 命中；drafts 面 "three-way" 命中 E331-draft-2301 经读全文确认为
**git 三方合并（three-way merge）**领域，语义假阳性，不构成覆盖；E130/E133
（nullptr_t/__abi_tag__）、E306（std::polar NaN）、E191（libc++ 链接）均不同主题。
无覆盖。

## 知识库沉淀价值

- 可复用问题类别：C++20 代码对标准容器用 `<=>`，在 OHOS clang15/libc++（缺
  实现）下编译失败。
- 适用对象：一切目标 OHOS 的 C++20 库（大量现代 C++ 项目使用 `<=>`）。
- 决策价值：一眼识别编译错误并套用"compare_string/compare_vector 等价 + 手写
  `<=>` 后显式补回 `operator==`"的完整性清单，避免踩 "defaulted 隐含 == 丢失"
  的二次坑。

## 方案

1. 在公共头提供 `compare_string` / `compare_vector` 两个可移植等价函数
   （语义 = 标准库 `<=>` 的字典序行为）。
2. 把对 string/vector/variant 的 `operator<=>` 改写为调用这两个函数
   （bali-phy 0002 共 9 处）。
3. 对原 `defaulted <=>` 的类型（Pattern/Alts/Constant/integer_container）按
   `(*this <=> v) == equal` 显式补回 `operator==`。
4. integer_container 用 `cpp_int.compare()` 代替（boost::multiprecision 自己的比较）。

## 验证证据

- 修复前：func.cc 编译失败（invalid operands to binary expression，Pattern/Constant
  缺 operator==）；改 0002 补全 operator== 后编译通过。
- 修复后：round-2~round-6 多轮全量编译链接通过；权威 round-6 CI
  218/218 + test_package 10/10 + create_exit_code=0。

## 禁止做法

- 为绕过错把 `cppstd=20` 降到 17：改变 ABI/语义并掩盖 C++20 依赖。
- 用 `#pragma`/汇编等与缺失标准库操作符无关的绕行手段。
- 把"三个容器缺 `<=>`"当成单个库的临时补丁：这是 OHOS toolchain 的通用能力缺口。
