# FLINT >= 3 已并入 arb 模块：旧版独立库的兼容适配（DRAFT）

## 问题

将 arb 2.9.0（FLINT 2.x 时代独立库）适配到 HarmonyOS PC（arm64, clang 15）
并链接 FLINT 3.6.0 时,出现一组成体系的编译/链接/运行期错误：

```
fmpz_extras.h:41: error: redefinition of 'fmpz_add_si'
fmpz_extras.h:120: error: static declaration of 'fmpz_set_mpn_large'
                    follows non-static declaration
fmpz_extras.h:147: error: unknown type name 'mp_bitcnt_t'
arf.h:392: warning: call to undeclared function 'flint_mpn_copyi'
ld.lld: error: -r and -pie may not be used together
Error relocating libarb.so.2: mpn_neg_n: symbol not found
Error relocating libarb.so.2: n_gcd_full: symbol not found
Error relocating libarb.so.2: FLINT_BIT_COUNT: symbol not found
```

## 根因

1. **FLINT 3.x 已并入 arb 模块**：flint/fmpz.h 等公共头内建了 arb 曾私有提供的
   `fmpz_add_si`/`fmpz_sub_si`/`fmpz_set_mpn_large`/`fmpz_ui_pow_ui`/
   `fmpz_kronecker` 等,与 arb 2.9.0 自带的 `fmpz_extras.h` 静态副本重复定义。
2. **FLINT 3 的头链收窄**：flint.h 只包含 stddef.h,不再传递包含 gmp.h /
   longlong.h / fmpz_vec.h / fmpq_vec.h / mpn_extras.h / ulong_extras.h,
   导致 `mp_bitcnt_t`、`EXIT_SUCCESS`、`flint_mpn_copyi`、`FLINT_BIT_COUNT` 未声明。
3. **符号改名/移除**：GMP >= 6.2 将 `mpn_neg_n` 改名为 `mpn_neg`;
   FLINT 3 移除了 `n_gcd_full`（仅保留 `n_gcd`）;
   `count_trailing_zeros`/`count_leading_zeros` 被 `flint_ctz`/`flint_clz` 取代。
4. **工具链默认 PIE**：OHOS clang 默认 `-pie`,与 arb 的模块级部分链接
   `$(CC) -Wl,-r` 冲突（`-r and -pie may not be used together`）。
5. **内部 API 签名变化**：FLINT 3 的 `_fmpz_poly_div` 增加 `int exact` 参数。

## 方案

用 `__FLINT_VERSION >= 3` 守卫做最小兼容层（本任务归档补丁 0001-0006）：

1. `fmpz_extras.h`：FLINT >= 3 时跳过 arb 自带重复定义,并补
   `#include <gmp.h> <stdlib.h>` 及 flint/longlong.h、fmpz_vec.h、
   fmpq_vec.h、mpn_extras.h、ulong_extras.h;
   提供 `count_trailing_zeros`/`count_leading_zeros` 别名到 flint_ctz/flint_clz,
   `mpn_neg_n`→`mpn_neg` 宏、`n_gcd_full`→`n_gcd` 内联。
2. `Makefile.subdirs`：模块部分链接加 `-no-pie`。
3. `sin_cos_pi_fmpq_algebraic.c`：`_fmpz_poly_div` 在 FLINT >= 3 传 6 参。
4. `epsilon_arg.c` / `bool_mat.h`：跳过 FLINT 3 已提供的静态副本、补 longlong.h。
5. 上游测试文件（bool_mat/dirichlet/dlog/arb t-*.c）：显式包含 `<stdlib.h>`、
   适配 `flint_mpn_rrandom` 的 `flint_rand_t` 签名。

## 验证

- `conan create`（OHOS aarch64）通过,test_package 1/1 通过（真实 arb API 断言）。
- 上游测试全量 667 项独立入口全部实例化并运行：662 通过、5 失败
  （fmpr t-root/t-sqrt/t-mul_naive ULP 舍入差异、arb t-set_str 解析、
  bool_mat t-all_pairs_longest_walk 幂次化）,662/667 = 99.25%。
- W2 结构完整、W3 本地 CI 门禁子项全 pass。

## 适用边界与反例

- 适用：基于 FLINT 2.x API 的独立库（arb ≤ 2.23 及同类）适配 FLINT 3.x,
  以及直接调用 `mpn_neg_n`/`n_gcd_full`/FLINT 内部 `_fmpz_*` 的旧代码。
- 反例/不适用：新库直接使用 FLINT 3 自带 arb（include/flint/arb.h）时无需
  此兼容层;FLINT 2.x 环境下不需要版本守卫分支。
- 升级 arb 到与 FLINT 3 兼容的后续版本可消除剩余 5 项测试断言差异。

## 关系

- similar_to: E014（仅“符号缺失”表面相似,实质为 musl syscall,已排除）
- caused_by: FLINT 3.x 并入 arb 模块
- prerequisite_of: 后续 FLINT 2.x 时代库的 HarmonyOS 适配
- conflicts_with: 无
