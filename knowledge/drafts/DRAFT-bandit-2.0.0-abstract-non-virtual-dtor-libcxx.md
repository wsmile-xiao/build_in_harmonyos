# DRAFT-bandit-2.0.0-abstract-non-virtual-dtor-libcxx：旧 C++11 抽象基类无虚析构在现代 libc++(-ohos) 下被 -Werror 拦截的通用修复

> Contributor: pc4-8 | Status: Draft | Updated: 2026-09-19
> Source: bandit 2.0.0 HarmonyOS PC adaptation（archives/b/bandit/2.0.0，r01）
> 对应：knowledge/drafts/DRAFT-bandit-2.0.0-abstract-non-virtual-dtor-libcxx.kv

## 现象

编译带 `-Werror` 的旧 C++11 三方库源码时，现代 libc++（含 OHOS SDK 的 libc++-ohos）
在 `std::unique_ptr<抽象基类>` 析构处报错：

```text
.../libcxx-ohos/include/c++/v1/__memory/unique_ptr.h:48:5: error:
  delete called on 'bandit::detail::failure_formatter' that is abstract
  but has non-virtual destructor [-Werror,-Wdelete-abstract-non-virtual-dtor]
```

## 根因分析

bandit 2.0.0（2015 年 C++11 代码）的抽象基类 `failure_formatter` 只有纯虚函数
`format()`，没有虚析构；却通过 `std::unique_ptr<failure_formatter>`
（`failure_formatter_ptr`）持有派生对象并 delete。通过基类指针 delete 派生对象而
基类无虚析构是未定义行为（UB）。现代 libc++ 对该 UB 提供编译期诊断；项目自身开启
`-Werror` 后诊断升级为硬错误，构建失败。

## 解决方案

最小补丁：为抽象基类增加虚析构（空实现即可），修复 UB 并满足编译器诊断：

```cpp
struct failure_formatter
{
  virtual ~failure_formatter() {}            // 补丁新增
  virtual std::string format(const assertion_exception&) const = 0;
};
```

落到 patches/：`git diff` 出补丁（refresh-patch --auto 可自动生成），conandata
patches 列表声明 `patch_file/patch_description/patch_type: portability`。

## 验证

- bandit 2.0.0：补丁后 `make bandit-specs` 编译通过，上游测试 310/314 通过；
  `conan create`（patch 应用）通过；消费者用例 `1/1 Test Passed`。
- 命令与退出码：`CMAKE_POLICY_VERSION_MINIMUM=3.5 make -C build bandit-specs`（exit 0）；
  `./build/bin/bandit-specs --no-color --reporter=dots`（exit 0，310 通过）。

## 适用边界 / 反例

- 适用：任何旧 C++11/C++03 头文件库或源码在 libc++-ohos / 新版 libc++ / libstdc++ 诊断
  增强下遇到 `-Wdelete-abstract-non-virtual-dtor`（或同族 `-Wabstract-vbase-init` 等）时，
  为抽象基类补虚析构是正确且通用的修复。
- 反例：类非抽象、无多态删除场景时不需要；用 `-Wno-delete-abstract-non-virtual-dtor`
  关闭诊断属于掩盖 UB，仅允许作为临时绕过并有记录。

## 查重与关系

- 本库四范围（index.tsv/graph/doc/drafts）检索 `delete-abstract|non-virtual destructor|virtual destructor` 均未命中。
- similar_to: 无；caused_by: 无；prerequisite_of: 无；conflicts_with: 无
- exact_duplicate=false, causal_duplicate=false, trigger_overlap=false, solution_overlap=false
- combination_novelty=true（抽象基类 `-Wdelete-abstract-non-virtual-dtor` × libc++-ohos 边界）