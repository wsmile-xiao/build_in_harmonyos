# DRAFT-cppnumericalsolvers-2.0.0-api-migration-dual-test-registration：header-only CRTP 库版本升级 API 迁移 + 双构建系统测试注册口径

> Contributor: pc4-16 | Status: Draft | Updated: 2026-09-25
> Source: cppnumericalsolvers 2.0.0 适配（Path B 知识库扩展，task cppnumericalsolvers-2.0.0-r01-pc4-16）
> 对应：`knowledge/drafts/DRAFT-cppnumericalsolvers-2.0.0-api-migration-dual-test-registration.kv`

## 现象

1. test_package 消费者按 1.0.0 API 写法（`cppoptlib::Problem<double,2>` /
   `BfgsSolver<Rosenbrock>` / `solver.minimize(f, x)`）编写 2.0.0 消费者，
   编译失败：

   ```text
   test_cppoptlib.cpp:20:48: error: no template named 'FunctionX2_dx' in namespace 'cppoptlib::function'
   class Rosenbrock : public cppoptlib::function::FunctionX2_dx<T, Rosenbrock<T>> {
   ```

   即使改用 `FunctionXd<F>` 也会因误用测试本地别名而出现
   `no member named 'VectorType'` 等级联错误。

2. 上游测试双口径台账显示：`src/test/CMakeLists.txt` 只注册
   `build_test(verify)` / `build_test(cstep_test)`，而 Bazel `BUILD` 完整注册
   5 个测试入口（verify/cstep_test/hager_zhang_test/trust_region_newton_test/
   augmented_lagrangian_test）。若按 CMake 注册口径，会少报 3 个测试文件
   （hager_zhang 4 + trust_region_newton 9 + augmented_lagrangian 27 = 40 个用例）。

## 根因

- cppnumericalsolvers 2.0.0 重构为 CRTP 接口：公开别名
  `cppoptlib::function::FunctionXd<F>`（= `FunctionCRTP<F, double, First>`）与
  `FunctionXf<F>`（float 一阶）；求解器改为
  `cppoptlib::solver::Lbfgs<F>::Minimize(f, cppoptlib::function::FunctionState(x))`，
  返回 `[solution, solver_state]`。1.0.0 的 `cppoptlib::Problem` /
  `BfgsSolver` / `minimize` 已移除。
- 上游 `src/test/verify.cc` 顶部自带 `FunctionX2` / `FunctionX2_dx` /
  `FunctionX2_dxx` 三个**测试本地便利别名**（对应 None/First/Second 可微模式），
  不是库公开 API——消费者照抄测试写法必然编译失败。
- 上游 CMake 测试注册未随新增测试文件同步（2.0.0 新增了 3 个测试文件但
  CMakeLists 未添加），Bazel BUILD 是完整权威注册。

## 修复（已验证）

1. **消费者一律用库公开 API**：

   ```cpp
   #include "cppoptlib/function.h"
   #include "cppoptlib/solver/lbfgs.h"

   class Rosenbrock : public cppoptlib::function::FunctionXd<Rosenbrock> {
    public:
     EIGEN_MAKE_ALIGNED_OPERATOR_NEW
     using typename cppoptlib::function::FunctionXd<Rosenbrock>::ScalarType;
     using typename cppoptlib::function::FunctionXd<Rosenbrock>::VectorType;
     ScalarType operator()(const VectorType& x, VectorType* grad = nullptr) const { ... }
   };
   // 求解
   auto initial_state = cppoptlib::function::FunctionState(x);
   cppoptlib::solver::Lbfgs<Function> solver;
   auto [solution, solver_state] = solver.Minimize(f, initial_state);
   ```

   编译命令：`clang++ -std=c++17 -O1 -I<repo>/include -I<eigen3>/include/eigen3 test_cppoptlib.cpp -o test_cppoptlib`
   运行结果：`min f=5.50803e-17 at (1.000000, 1.000000) status=3` → PASS。

2. **测试枚举按权威完整注册（Bazel BUILD）**：5 个测试入口全部编译运行，
   双口径 `64/64 (100%)`（verify 17 + cstep 7 + hager_zhang 4 +
   trust_region_newton 9 + augmented_lagrangian 27），无未实例化/未运行项。

## 适用边界 / 反例

- 适用：header-only CRTP 模板库的消费者验证与 test_package 编写；测试文件
  自带便利别名的库；CMake 与 Bazel 双构建系统并存且注册不一致的库。
- 反例：纯 C 库、单一构建系统库、非模板接口库（不存在"测试本地别名 vs 公开
  API"边界）；CMake 注册完整时无需 Bazel 兜底。
- 若不满足上述条件，本知识不触发，不应硬套。

## 验证命令

```bash
grep -rn "using FunctionX2" <src>/src/test/verify.cc      # 测试本地别名证据
grep -n "build_test" <src>/BUILD                          # Bazel 完整注册证据
grep -n "build_test" <src>/src/test/CMakeLists.txt        # CMake 注册不全证据
clang++ -std=c++17 -O1 -I<repo>/include -I<eigen3> test_cppoptlib.cpp -o t && ./t
```
