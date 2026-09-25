# DRAFT-containers-1.2.2-makefile-test-gcc-to-clang-tautological-warning

## 症状

上游 Makefile 测试目标（C89 库）在无 gcc 的 OHOS 平台直接失败的两种表现：

```
# 失败一：测试目标硬编码 gcc 不存在
$ make test_optimized
/bin/sh: gcc: inaccessible or not found
make: *** [Makefile:29: test_optimized] Error 127

# 失败二：换用 clang 等价编译后被 clang 独有诊断在 -Werror 下拦截
$ clang src/*.c tst/*.c -Wall -Wextra -Wpedantic -Werror -std=c89 -O3 -ldl -o ContainersTest
src/set.c:455:37: error: result of comparison of constant -1 with expression of type 'char' is always false [-Werror,-Wtautological-constant-out-of-range-compare]
            if (!parent || child[0] == -1 || child[0] == 1) {
```

## 根因

1. **OHOS PC 平台只有 clang，没有 gcc**：上游 Makefile 的测试目标硬编码
   `gcc src/*.c tst/*.c -Wall -Wextra -Wpedantic -Werror -std=c89 -O3 -ldl -o ContainersTest`，
   直接执行即 exit 127。
2. **clang 独有诊断**：`-Wtautological-constant-out-of-range-compare` 在 gcc 上不存在。
   OHOS AArch64 的 plain char 默认为**无符号**，`char == -1` 恒假，clang 在 `-Werror`
   下将此判为硬错误；gcc 从不触发该诊断，因此这是编译器差异而非上游源码缺陷。
3. **配套问题**：若源码用 plain char 存有符号状态（如 set.c 的 AVL 平衡因子
   -1/0/1），无符号 char 还会导致运行期断言失败（`right - left == item[0]`），
   需 `-fsigned-char` 一并恢复上游语义。

## 方案

用与上游 gcc 命令**完全等价**的 clang 参数编译，仅追加两项：

```bash
clang src/*.c tst/*.c -Wall -Wextra -Wpedantic -Werror \
  -Wno-tautological-constant-out-of-range-compare -fsigned-char \
  -std=c89 -O3 -ldl -o ContainersTest && ./ContainersTest
```

- `-Wno-tautological-constant-out-of-range-compare`：抑制 clang 独有的比较诊断，
  保留上游 `-Werror` 严格度覆盖其余真实问题。
- `-fsigned-char`：OHOS AArch64 上恢复上游 x86 的 signed-char 语义（E419 同族）。

不改上游测试源码、不降级 `-std/-Werror` 门禁。

## 验证

- 缺失 `-Wno-tautological` 时：`src/set.c` 报 8 个 `-Werror` 错误（复现闭环）。
- 追加两项后：编译 exit 0，`./ContainersTest` 输出 `Tests Passed`，上游
  16/16 独立用例全过（source_declared_total=16, executed_passed=16, 100%）。

## 适用边界 / 反例

- 适用：上游测试目标硬编码 gcc；OHOS/无 gcc 平台；源码含 plain char 与负数
  比较（无符号目标 + clang -Werror）。
- 反例/不适用：平台本身有 gcc 时无需替换；`-Werror` 之外的其他真实源码错误
  不能用 `-Wno-*` 掩盖；不能把 `-Wno-*` 写进正式发布配方掩盖真实告警
  （仅限与上游完全等价验证路径的测试编译）。

## 关系

- `similar_to`：E265（OHOS 无系统工具时上游测试的替代执行）、
  E359（gcc 缺失时的构建机编译器映射）
- `related`：E392（raw makefile Conan 配方三坑，含 compiler_executables 字典与
  cwd=self.source_folder）、E419（AArch64 plain char 无符号性，-fsigned-char 通用修复族）
- 配套注意点（C4，来自同一 raw makefile 配方适配族）：上游产物无 lib 前缀
  （`containers.a`）时，Conan 包安装需重命名 `libcontainers.a` 供 CMakeDeps
  `find_library` 消费（与 DRAFT-libsnd 的 cpp_info 去前缀是互补方案）。