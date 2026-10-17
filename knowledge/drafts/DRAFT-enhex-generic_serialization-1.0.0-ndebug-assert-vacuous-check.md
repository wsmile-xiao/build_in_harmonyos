# DRAFT-enhex-generic_serialization-1.0.0-ndebug-assert-vacuous-check

## 问题 (Problem)

Conan test_package 的测试入口(例如 `test.cpp` / `harmony_platform_test.cpp`)若只依赖 `assert()` 承载正确性校验,在 CI 实际使用的 `Release`(含 `-DNDEBUG`)构建下,`assert` 整体被编译剥离(C 标准:NDEBUG 下 `assert(EXPR)` 展开为 `((void)0)`),任一校验失败都**静默通过**——`main()` 恒 `return 0`,测试对序列化/序列化往返回归的检出能力为零,效果等同伪造通过。外部代码审查可据此判定 High Priority 阻塞。

## 根因 (Root Cause)

- `assert` 是条件编译宏:`-DNDEBUG`(Release 构建的 CMake/Conan 默认)下其表达式不求值、`assert` 调用不产生任何代码。
- 测试源码没有独立的失败路径:校验失败时唯一表现是 assert abort,剥离后无任何输出、无非零退出。
- `test_package/CMakeLists.txt` 未做 `-UNDEBUG` 或 `target_compile_options` 补偿,测试目标以 `Release` 配置编译:
  `cmake -DCMAKE_BUILD_TYPE="Release"`,构建目录名如 `build/clang-15-armv8-17-release`。
- 仅靠"测试确实链接了被测包"(L1e 破坏式负例)不覆盖正确性:链接存在 ≠ 结果被校验。

## 方案 (Solution)

让测试入口的**全部**正确性校验在 Release/NDEBUG 下无条件求值,失败时**非零退出且可定位**:

1. 不依赖 `assert` 承载正确性:定义不随 NDEBUG 失效的 `CHECK(cond, what, expected, actual)` 宏(宏体内无 assert、无 `#ifdef NDEBUG` 分支),逐项核对并打印 `FAIL: <字段> expected=... actual=...`,累计失败数,`main()` 末尾 `if (failures != 0) return 1;`。
2. 校验不得被优化器消除:校验结果必须被实际分支依赖(累计计数 + 返回码),禁止"赋值后被丢弃"。
3. 覆盖范围不回退:校验项数 ≥ 改造前 assert 数;字节完整性类校验须按**序列化实际写入字节数**(逐字段 `sizeof` 之和)而非 `sizeof(结构体)`(结构体含尾部对齐填充,gs 逐字段写入不含填充)。
4. `-UNDEBUG` 补偿本身不充分(其它构建路径仍会剥离),优先无条件检查。

## 验证 (Verification)

双向对照(同一 Release/NDEBUG 配置):

- **配置取证**:`conan create` 日志 `build_type=Release`、`-DCMAKE_BUILD_TYPE="Release"`、构建目录名含 `-release`;编译标志含 `-DNDEBUG`(CMakeCache/flags.make/实际命令行)。
- **负向对照**(worktree 外):复制测试源码,注入确定性字段错位(如期望值改为不可能值),同 `-O3 -DNDEBUG` 编译运行 → **exit 1**,stderr 输出 `FAIL: dst.x expected=999 actual=5`;注入产物不进入 worktree/暂存区/commit。
- **正向对照**:未注入修复版同配置编译运行 → **exit 0**,日志打印 `checks=N failures=0` 证明校验实际执行。

## 适用边界 (Applicability)

- 适用于所有 Conan/CMake `Release`(NDEBUG)构建下运行的 C/C++ test_package 测试入口。
- 同样适用于设备原生以 `-O3 -DNDEBUG` 编译运行的测试/示例。
- 不适用于故意依赖 NDEBUG 关闭断言以测量性能的基准类程序。

## 反例与限制 (Counter-examples & Limitations)

- 仅加 `-UNDEBUG` 而不消除 assert 依赖:其它构建路径仍剥离,且 `assert(expr)` 中 expr 的副作用会被跳过(E259 已有该角度,但 E259 侧重上游源码 assert 含副作用,本轮侧重测试代码唯一校验依赖 assert 的空壳化)。
- 失败只打印仍 `return 0`:违反本模式,一律视为空壳。
- 校验结果赋值给未使用变量:可能被优化器消除。

## 查重差异 (Dedup Difference vs E259)

- E259:`assert(含副作用的表达式)` 被 NDEBUG 剥离 → 上游 **latent bug 触发**(断言**失败**暴露错误),方案是 hoist-side-effect-out-of-assert。
- 本条目:测试**唯一**正确性校验依赖 assert → NDEBUG 剥离 → **静默恒通过**(断言**从不失败**),方案是 unconditional CHECK + 非零退出。错误特征相反(FAIL 缺失 vs 大量 FAIL),修订对象是测试代码而非上游源码。