# DRAFT-mlp.h-0.10.0-conan2-testpkg-check-kwarg — Conan 2.x test_package 配方 API 变化 + 严格 C99 M_PI 编译边界

## 问题现象

mlp.h 0.10.0（单头文件 C99 MLP 库）在 OHOS armv8 上做 Conan 2.x 适配时，遇到
两条与库本体无关、可跨库复用的配方/编译陷阱：

```
# (1) test_package 中 self.run(check=True) → Conan 2.x TypeError
TypeError: ConanFile.run() got an unexpected keyword argument 'check'
  File ".../test_package/conanfile.py", line 28, in build
    self.run(f"{cc} ... -o {exe} -lm", check=True)

# (2) clang 严格 c99 下 M_PI 未定义
visual_sin.c:43:30: error: use of undeclared identifier 'M_PI'
    Dataset TR_D = init_data(TR, true);   ← TR 展开为 2 * M_PI
```

## 根因分析

1. **Conan 2.x 移除 `check` 参数**：`ConanFile.run()` 在 Conan 2 中不再接收
   `check` 关键字参数——任何非零退出码**默认**抛 `ConanException` 中断构建。
   沿袭 Conan 1.x 写法 `self.run(cmd, check=True)` 会直接 `TypeError`，且发生在
   test_package `build()` 早期，掩盖真实编译错误。
2. **M_PI 与 `_USE_MATH_DEFINES`**：`M_PI` 是 POSIX/BSD 扩展宏，glibc 仅在
   `-std=gnu*`（或定义 `_GNU_SOURCE`/`_DEFAULT_SOURCE`）下导出；`_USE_MATH_DEFINES`
   是 **MSVC 专用**宏，在 clang `-std=c99` 下无效。上游样例 `visual_sin.c` 用
   `_USE_MATH_DEFINES` 期望在严格 C99 下拿到 `M_PI`，clang 直接报未定义。

## 方案

1. **test_package 中 `self.run` 一律不传 `check=`**，依赖 Conan 2 默认的非零
   退出码抛错语义；确需忽略失败时再考虑 `ignore_errors`（非推荐）：

   ```python
   def build(self):
       self.run(f"{cc} -std=c99 -O2 -I{inc} {src} -o {exe} -lm")
   ```

2. **编译使用 M_PI 的上游源码/样例用 `-std=gnu99`**（或 `-D_GNU_SOURCE`），
   不改上游源码；仅当库严格要求 C99 时才在源码内自行定义 M_PI：

   ```bash
   clang -std=gnu99 -O2 visual_sin.c -o visual_sin
   ```

## 验证（mlp.h 0.10.0 本轮真实日志）

1. 删除 `check=True` 后 `conan create` G2 PASS，test_package 编译链接运行
   退出码 0（`$TMPDIR/oh-pc1-6-mlp/conan_create7.log`，XOR 验证
   max_error=0.0033 PASSED）。
2. `-std=gnu99` 编译 `visual_sin.c` 通过并运行收敛（Final Loss 1.06e-04，
   rc=0，`visual_sin.run.log`）；`-std=c99` 复现 M_PI 未定义错误。

## 适用范围与边界

- 所有 Conan 2 编写 test_package 的配方（`self.run` 调用处）；
- 任何在 clang 严格 c99 下编译使用 `M_PI` 的上游 C 源码/样例；
- 边界：Conan 1→2 API 迁移边界；`-std=gnu99` vs `-std=c99` 严格模式边界。
  若库本身要求严格 C99 且无法改用 gnu99，则在源码内自行 `#define M_PI`。

## 查重（七轴）

| 轴 | 结论 |
|---|---|
| exact_duplicate | false（图谱/doc 无 `check=True` TypeError 条目；M_PI 精确检索零命中） |
| causal_duplicate | false |
| trigger_overlap | false |
| solution_overlap | false |
| combination_novelty | true |
| boundary_novelty | true（Conan 1→2 API 边界 / 严格 c99 边界） |
| test_migration_novelty | false |

- similar_to: E239（self.run fail-fast 语义，但未覆盖 check= 参数移除）、
  E311、E340、DRAFT-boost-te-1.0.0-headeronly-copy-abs-path-commit-incremental
- caused_by: [] / prerequisite_of: [] / conflicts_with: []
- 决定: `new_draft`（路径 B，与 mlp.h 归档进同一 PR）
