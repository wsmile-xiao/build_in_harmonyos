# DRAFT: C++17 下 register 关键字位于安装的公共头文件时须源码补丁

- **stem**: coinor-vol-1.5.4-register-installed-public-header-cpp17
- **状态**: DRAFT（需人工/AI 复核后可 promote 为 E 条目）
- **来源事件**: coinor-vol 1.5.4 HarmonyOS PC (arm64) 适配（conan-verify G2 实测）
- **关联正式条目**: E293（同根因，但仅覆盖 toolchain-flag 与 src/*.cpp fallback）

## 问题

2003 年代 C++ 代码使用 `register` 存储说明符。OHOS 编译 profile 固定
`compiler.cppstd=17`，clang `-std=c++17` 下该特性从 warning 升级为 hard error：

```
error: ISO C++17 does not allow 'register' storage class specifier [-Wregister]
```

当 `register` 位于**被安装到公共 include 目录的头文件**（如
`include/coin/VolVolume.hpp`）时，问题放大：消费者以 cppstd=17 包含该头文件
同样编译失败。库自身的 `-Wno-error=register` toolchain-flag 无法保护消费者。

## 根因

1. 上游代码使用 C++17 已移除的 `register` 说明符（模板函数参数 + 局部变量）。
2. 关键字位于安装头文件 → 影响面从"库内部编译"扩展为"所有消费者编译"。
3. E293 的 primary 方案（toolchain-flag）只作用于库构建期，未覆盖该边界。

## 方案

源码层补丁移除 register（模板参数与局部变量均需覆盖），补丁随配方
`exports_sources` 打包并在 `apply_conandata_patches` 应用；test_package 消费者
以 cppstd=17 包含头文件做反向验证。

coinor-vol 1.5.4 实测补丁（0005-register-remove.patch，Vol/src/VolVolume.hpp 3 处）：

```diff
-VolMax(register const T x, register const T y) {
+VolMax(const T x, const T y) {
-VolAbs(register const T x) {
+VolAbs(const T x) {
-      register const double ll = VolAbs(lcost);
+      const double ll = VolAbs(lcost);
```

## 验证

- `clang++ -std=c++17 -stdlib=libc++ -Wall` 编译 libVol rc=0 且 0 警告
- conan-verify G2 干净构建 PASS（含 test_package）
- test_package 消费者（CMakeDeps + cppstd=17 包含头文件）1/1 Test Passed
- 安装后头文件 `grep -c '\bregister\b'` = 0

## 适用边界 / 反例

- **适用**: register 位于安装公共头文件的 2003 年代 C++ 库（消费者受影响）
- **反例（可用 toolchain-flag）**: register 仅存在于库内部 .cpp（不被安装的
  头文件不包含），E293 primary 方案即够
- **禁止**: `--build/--host` 绕过（误判交叉编译）；`CMAKE_CXX_STANDARD 11`
  降级掩盖（profile 固定 17）

## 与既有知识差异（查重七轴摘要）

- `causal_duplicate=yes`（根因与 E293 同源：register + C++17）
- `solution_overlap=partial`（E293 primary=toolchain-flag 在本场景不充分；
  source-patch 为其 fallback 但未区分安装头文件消费者边界）
- `boundary_novelty=yes`（新边界：安装公共头文件 → 必须源码补丁；消费者包含
  头文件是决策关键）
- `similar_to=E293`，非完整重复，可跨库复用

## 建议 promote 动作

复核本草稿后：移至 `knowledge/graph/E0XX.kv`、写 `knowledge/doc/E0XX.md`、
登记 `knowledge/graph/index.tsv`，并在 E293 条目中补充"安装头文件边界"指针。
