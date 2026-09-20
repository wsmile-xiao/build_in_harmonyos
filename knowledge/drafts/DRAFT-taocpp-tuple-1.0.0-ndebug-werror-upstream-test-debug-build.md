# DRAFT-taocpp-tuple-1.0.0-ndebug-werror-upstream-test-debug-build：上游测试 Release(NDEBUG) 下 assert 编译为空 → -Werror unused variable，需 Debug 构建实际运行上游用例

> Contributor: pc4-8 | Status: Draft | Updated: 2026-09-19
> Source: taocpp-tuple 1.0.0 适配（task taocpp-tuple-1.0.0-r01-pc4-8-20260919T132234Z）
> 对应：`knowledge/drafts/DRAFT-taocpp-tuple-1.0.0-ndebug-werror-upstream-test-debug-build.kv`

## 问题

在 OHOS/CI 干净环境下实际运行上游测试时，上游测试目标用 Release（-DNDEBUG）
构建会报：

```
src/test/tuple/tuple_main.cpp:18:9: error: unused variable 't5' [-Werror,-Wunused-variable]
   auto t5 = tuple< int, double, int >( 1, 2, 4 );
```

同一份源码在普通 Linux 发行版（不带 NDEBUG 跑测试）下从不报错。若把该错误
误记为"测试失败"或"上游测试不可运行"，会扭曲上游测试通过率。

## 根因

上游 CMake 测试目标常带严格告警升级：

```cmake
target_compile_options(test PRIVATE -pedantic -Wall -Wextra -Wshadow -Werror)
```

Release 构建注入 `-DNDEBUG` 后，`assert(EXPR)` 展开为 `((void)0)`，表达式被整体
删除。仅被 assert 引用（如 `assert(t2 < t5)`）的变量 `t5` 在断言消失后成为
"未使用变量"，`-Werror` 把该 warning 升级为编译错误。

关键判别：**这是"断言被编译掉"的构建配置问题，不是用例失败**。断言在 Debug
构建下全部生效并通过，即用例真实通过。

与 E259（Conan Release 的 -DNDEBUG 让 assert(含副作用的表达式) 不求值）区分：
- E259：assert 内**含副作用表达式**（赋值/调用），NDEBUG 下副作用不求值 → **运行时行为错误**（latent bug），方案是 hoist-side-effect-out-of-assert
- 本候选：assert 本身被编译掉 → 仅被 assert 引用的**变量**变成 unused → **编译期错误**，方案是 Debug 构建实际运行上游测试

## 方案

上游测试用 **Debug 构建**实际运行（assert 生效）：

```bash
cmake -DCMAKE_BUILD_TYPE=Debug -D<UPSTREAM_TESTS>=ON   # 如 -DTAOCPP_TUPLE_BUILD_TESTS=ON
cmake --build . -j4
ctest --output-on-failure
```

## 验证（taocpp-tuple 1.0.0 实证）

Release 构建：`tuple_main.cpp:18: error: unused variable 't5' [-Werror,-Wunused-variable]`（2 errors，构建失败）
Debug 构建：

```
cmake --build . -j4        # 3 个测试目标全部链接成功
ctest --output-on-failure
1/3 Test #1: tuple_benchmark ... Passed    0.02 sec
2/3 Test #2: tuple_cat ...... Passed    0.02 sec
3/3 Test #3: tuple_main ..... Passed    0.02 sec
100% tests passed, 0 tests failed out of 3
```

双口径：source_declared_total=3，configured_executable_total=3，executed_passed_total=3，
全量通过率 3/3=100%。

## 适用边界

- ✅ 适用：上游测试用 assert + `-Werror` 编译，需要在 OHOS/CI 干净环境实际运行上游用例的库
- ✅ 与 E259 可区分：E259 看"运行时行为错误 + assert 副作用"，本候选看"编译期 unused variable + assert 被编译掉"
- ⚠️ 反例/不适用：上游测试不含 assert（如用独立测试框架）、或未启用 -Werror 时不会触发；此时无需 Debug 构建
- ⚠️ 不适用：上游测试依赖 Release 宏/优化行为（如 `#ifdef NDEBUG` 分支）时，Debug 构建会改变测试语义，按 fallback 处理

## 查重差异（七轴）

| 轴 | 结果 | 说明 |
|---|---|---|
| exact_duplicate | false | 无既有条目精确命中 |
| causal_duplicate | false | 根因不同：编译期 assert 消失 vs E259 运行时副作用不求值 |
| trigger_overlap | true | 同 NDEBUG 触发面，但触发场景不同（编译期 vs 运行时） |
| solution_overlap | false | Debug 构建 vs E259 hoist-side-effect / E063 禁 warning |
| combination_novelty | true | NDEBUG×-Werror×unused variable 组合无既有覆盖 |
| boundary_novelty | true | 适用边界（assert 仅被断言引用 + -Werror）可区分于 E259 |
| test_migration_novelty | true | 上游测试迁移到 OHOS/CI 时首次记录该构建配置陷阱 |

## 关系

- `similar_to`：E259（NDEBUG + assert 相关，根因不同）
- `similar_to`：E063（-Werror warning 升级，方案不同）
- `prerequisite_of`：上游测试双口径台账（Test Ledger）在 OHOS/CI 环境下的真实运行
