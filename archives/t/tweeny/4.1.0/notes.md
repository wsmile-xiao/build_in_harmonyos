# tweeny 4.1.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only 库，INTERFACE target + install/export 规则）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4（OHOS SDK，target aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤
1. `source()`：GitHub tag v4.1.0 tarball（sha256 110903c6b5e2a68b28927c0ecf0c504d1b682fcd451f874880448857311a88b4）；OHOS 侧经 conan-verify E017 镜像注入后恢复官方 URL
2. `generate()`：CMakeToolchain 关闭 `TWEENY_BUILD_DOCUMENTATION/SINGLE_HEADER/TESTS`
3. `build()`：`cmake.configure()` → `cmake.build()`（INTERFACE 库无编译单元，验证配置阶段可用）
4. `package()`：`cmake.install()` → `include/tweeny/*.h/.tcc` + `lib/cmake/Tweeny/*.cmake`（NAMESPACE tweeny:: → `tweeny::tweeny`）；LICENSE 拷到 `licenses/`（absolute dst，避免模板相对路径坑）

## 存在的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 前 init-build 下载仓库页 URL 返回 HTML | 决策树 `--url` 传的是 repo 页而非 tarball | 用官方 tarball（`/archive/refs/tags/v4.1.0.tar.gz`）重跑 init-build |
| 2 | G2 conan create 报 `no member named 'onStep'` + `during() parameters must be of type uint32_t` + `during() must have one frame count per tween component` | v4 API 与 v3 不兼容：事件接口改为 `t.on(event::step, cb)`（回调签名 `event::response(tween&)`）；`during()` 强约束 uint32_t 且帧数必须与组件数一致 | 消费者测试改为 v4 API：`during(10u)`、`t.on(tweeny::event::step, [](const auto& t){ ...; return tweeny::event::response::ok; })`，测试内 peek 取值 |
| 3 | 本地/远端 CMake 4.x 接受 `cmake_minimum_required(VERSION 3.23...3.28)` | v4.1.0 最低版本 3.23 ≥ 3.5 策略线 | 无需 E103 注入（v3 的 3.0 才需要）；conan verify 与本地直接构建均通过 |

## 源码修改
无（`patches` 为空，上游源码未改动）

## 依赖版本
无第三方依赖（header-only，上游声明 Zero external dependencies）；测试期消费 Catch2/3.8.1（ohpcd 制品，仅测试用）

## 验证结果

```bash
# 上游测试（独立于配方构建，Catch2 v3 套件）
cmake -DTWEENY_BUILD_TESTS=ON -DCMAKE_PREFIX_PATH=<catch2-3.8.1-pkg> ..
cmake --build . --target tweeny_tests && ctest
# → 135/135 PASSED（100%，1.75s）—— 见 tmp/builds/tweeny-4.1.0.work/build-tests

# 配方验证
python3 scripts/ohc-run.py conan-verify tweeny 4.1.0   # Verdict: PASS（G0-G4 + L2/L4/L5）
# test_package: ctest 1/1 Test #1: test_tweeny ... Passed + ALL CHECKS PASSED（17 断言）

# 鸿蒙专项测试（tests-ohos/ohos_test.cpp，真实编译运行）
clang++ -std=c++17 -I<installed-include> -o ohos_test ohos_test.cpp && ./ohos_test
# → 17/17 PASS，exit 0 —— 见 tmp/tweeny-ohos-special-410/run.log
```

- 上游测试统计（双口径）：源码声明 135 个 TEST_CASE（28 个 .cpp，无 TEMPLATE_TEST_CASE）→ 当前配置实例化 135 个 ctest 注册项 → 实际执行 135/135 全过（135/135 = 100% 全量通过率）
- 消费者测试（test_package）：1 个程序 / 17 条断言全过
- 鸿蒙专项测试：17 条断言全过（线性插值、多值 tween、easing 形状、seek/step 语义、event::step 回调、越界钳制）
- L2/L4/L5 对 header-only 包跳过（无二进制产物、无包 cache id），属预期，非门禁失败

## 注意事项
- 下游引用 `tweeny/4.1.0`；`find_package(Tweeny)` + `target_link_libraries(app tweeny::tweeny)`；`#include <tweeny/tweeny.h>`
- v4 API 破坏性变更（相对 v3）：事件接口 onStep→on(event::step)、during 帧数类型强约束；已有 v3 消费者升级需适配
- 上游 v4.1.0 测试套件依赖 Catch2 v3，配方构建保持 TESTS=OFF 避免制品引入测试依赖
---

**编译结束**: 2026-09-19 13:16
**最终状态**: built
