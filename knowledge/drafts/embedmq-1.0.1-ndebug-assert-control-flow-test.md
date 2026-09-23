# embedmq 1.0.1 — test_package 测试用 assert 承载控制流前置检查在 NDEBUG 下静默失效

> Draft: DRAFT-EMBEDMQ-0101-NDEBUG-ASSERT-CONTROL-FLOW-TEST
> Stem: `embedmq-1.0.1-ndebug-assert-control-flow-test` — pairs with the same-stem `.kv`
> Observed: pc1-27 (AtomCode oh-executor embedmq 1.0.1 R01, 2026-09-22)

## 基本信息

- **ID**: DRAFT-EMBEDMQ-0101-NDEBUG-ASSERT-CONTROL-FLOW-TEST
- **严重度**: 2
- **类别**: testing|test_package|release|ndebug
- **触发工具**: conan|conan create|ctest|test_package|clang
- **阶段**: testing|test_package

## 错误特征（真实日志）

鸿蒙专项测试 test_ohos.c 首版把前置检查写成 assert：

```c
embedmq_t *q = embedmq_create(NULL);
assert(q != NULL);
...
assert(pthread_create(&th[i], NULL, producer, q) == 0);
...
assert(delivered > 0);
```

行为随是否定义 NDEBUG 截然不同（与 -O 优化等级无关）：

```
$ clang -O2 -std=c11 test_ohos.c libembedmq.a -pthread -o t && ./t      # 无 NDEBUG
[OHOS-SPECIAL] producers=4 msgs_per_producer=250 delivered=1000 last_value=247
[OHOS-SPECIAL] PASS ...                                                  # exit 0

$ clang -O2 -DNDEBUG -std=c11 test_ohos.c libembedmq.a -pthread -o t && ./t   # Release 等价
Signal 11 (core dumped)                                                  # exit 139

$ clang -O3 -DNDEBUG ...                                                  # 同样 SIGSEGV (139)
$ clang -fsanitize=address -O1 -DNDEBUG ...                               # delivered=0 却打印 PASS (exit 0，假通过)
```

Conan CI/W3 的 build_type=Release 默认注入 `-DNDEBUG`（flags.make 实证：
`C_FLAGS = -fPIC -O2 -O3 -DNDEBUG`），因此本地手工编译（无 NDEBUG）全过、进 conan test_package
就稳定 SIGSEGV，ctest 报 `***Exception: SegFault`，W3/conan-verify G2 全红。

## 根因

C11 `assert(EXPR)` 在 `NDEBUG` 下展开为 `((void)0)`，EXPR 不求值。测试把"关键前置条件"
（create 结果、pthread_create 成败、可观察后置量）寄托在 assert 上，Release 构建下：

1. 前置检查消失 → 错误路径不再短路：对 NULL / 未创建句柄继续操作（join 未初始化的
   `pthread_t th[]`）→ 稳定 SIGSEGV。
2. 后置断言消失 → 计数为 0 仍打印 PASS → **假通过**（ASAN 实证 delivered=0 却 exit 0）。

## 修复（规范化模式，可跨库复用）

全部前置/后置检查改为显式错误码 + 非零退出码，assert 只留在纯不变量处（或全部显式化）：

```c
embedmq_t *q = embedmq_create(NULL);
if (!q) { fprintf(stderr, "[TEST] FAIL: create returned NULL\n"); return 2; }

int r = embedmq_register(q, "evt", handler, NULL);
if (r != EMBEDMQ_OK) { fprintf(stderr, "[TEST] FAIL: register rc=%d\n", r); return 2; }

pthread_t th[N];
for (int i = 0; i < N; i++)
    if (pthread_create(&th[i], NULL, producer, q) != 0) { /* cleanup */ return 2; }

/* ... join producers, destroy, then: */
if (delivered <= 0) { fprintf(stderr, "[TEST] FAIL: no delivery\n"); return 2; }
printf("[TEST] PASS ...\n");
return 0;
```

判定以退出码为准；[PASS]/[FAIL] 文本仅作日志可读性。修改落在测试源文件，不改变被测库。

## 验证

- 重写后 `-fPIC -O2 -O3 -DNDEBUG`（与 CI flags.make 完全一致）连续 5 次运行 exit 0，
  delivered 均 > 0。
- conan create 内 test_package ctest：`2/2 Test passed`（test_embedmq + test_ohos），
  日志留档 `archives/e/embedmq/1.0.1/reports/conan-create.log`。
- 手工对照：无 NDEBUG 与有 NDEBUG 行为一致（均 PASS）。

## 适用范围 / 边界

- 适用：所有用 C assert 做测试前置/后置检查的 test_package、消费者用例、鸿蒙专项测试；
  任何以 Conan Release（-DNDEBUG）构建并跑 ctest 的配方。
- 边界：上游源码内 assert(含副作用表达式) 的问题归 E259（hoist-side-effect-out-of-assert），
  本条目聚焦**测试代码**用 assert 做控制流的构造缺陷，两者触发域部分重叠但方案不同。
- 反例：把关键检查写成 assert 且只在本地无 NDEBUG 环境验证 → CI/Release 下崩溃或假通过。

## 查重差异（与既有条目）

- E259（assert 副作用被 NDEBUG 编译掉，上游源码 latent bug）：触发域部分重叠（NDEBUG×assert），
  但 E259 面向"assert(含赋值/函数调用等副作用的表达式)"的**源码**修复（hoist 副作用）；
  本候选面向"测试代码用 assert 做控制流前置检查"的**测试构造**修复（显式错误码 + 退出码），
  属新增边界（boundary_novelty=true），两者互补不冲突。
- 知识图谱引擎对 `assert NDEBUG test_package` 命中 E259 外无其他遮挡；
  `Signal 11|core dumped` 类无既有测试构造条目。

## 关系

- similar_to: E259
- caused_by: （无既有条目；标准断言语义 + Release 构建组合）
- prerequisite_of: （无）
- conflicts_with: （无）