# DRAFT-libbig_int-2.6-bignum-clear-zeros-contract

> 草稿（Path B 知识库扩展）：bignum 算术结果长度不规范化导致溢出误判的 API 契约知识。待 promote。

## 问题

libbig_int 消费者用例中，`big_int_add` 后直接 `big_int_to_int` 返回 rc=1（溢出），
但数值本身完全正确（调试确认 `r->num[0]=19134`）。同现象出现在 `big_int_mul`、
`big_int_div` 结果导出时。

## 根因

`big_int_create(8)` 创建的答案对象 `len=8`；`addsub`/`mul` 计算后**不自动清掉高位的
零 word**，`r->len` 仍为 8。`big_int_to_int` 的溢出判定是：

```c
if (sizeof(num) < a->len * BIG_INT_WORD_BYTES_CNT) result = 1;  // 溢出
```

`len=8` → `8*4 = 32 > sizeof(int)=4` → 一律误判溢出。这是"结果长度未规范化"导致的
溢出误判，不是数值错误。

## 方案（消费者契约）

导出为 int 之前先调用公开 API 规范化长度：

```c
big_int_add(a, b, r);
big_int_clear_zeros(r);      /* 规范化 r->len */
big_int_to_int(r, &v);       /* 此时 v 正确 */
```

实测：加入 `clear_zeros` 后 12345+6789=19134、12345*6789=83810205、
83810205/12345=6789、gcd(1071,462)=21、十进制串往返 "987654321" 全部断言通过
（10/10，exit 0）。`big_int_to_str`/`big_int_from_str` 按实际数值处理，不受影响，
可作为绕过路径。

## 适用边界

- 适用：直接消费 libbig_int 并把结果导出为 int 的消费者/test_package 用例；
  同类"算术结果长度不自动规范化"的 bignum 库。
- 不适用：数值真的超过 int 范围（此时 rc=1 是正确行为）；使用 to_str 串导出
  验证的场景（无需 clear_zeros）。

## 查重差异

- 与 E398（libXext XSyncValueSubtract 溢出标志消费者契约）同属
  "消费者测试 / API 结果边界" 域：E398 是溢出标志误判（1-2 结果为精确 -1），
  本条是长度未规范化导致溢出误判（数值正确、判定错误），库、API、修复动作
  完全不同，方案不可互用，属部分覆盖 + 新增差异。

## 关系

- similar_to: E398
- caused_by / causes / conflicts_with: 无