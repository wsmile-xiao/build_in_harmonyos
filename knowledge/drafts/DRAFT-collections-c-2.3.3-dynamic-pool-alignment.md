# DRAFT-collections-c-2.3.3-dynamic-pool-alignment

> Contributor: pc4-6 | Status: Draft | Updated: 2026-09-06
> Source: collections-c 2.3.3 HarmonyOS PC 适配（R01，OHOS 专项测试 test_ohos_adapt.c）
> 领域：C 内存池（Collections-C cc_dynamic_pool）对齐契约

## 背景

Collections-C 2.3.3 的 `cc_dynamic_pool` 提供 `is_packed` / `alignment_boundary` 配置。
HarmonyOS 适配的鸿蒙专项测试以 16 字节对齐边界（与 aarch64-ohos libc `max_align_t` 一致）
配置非 packed 池并分配 1~1000 字节多种尺寸，实测 **连续分配块全部未对齐 16 字节**
（mod16 ∈ {1,2,8,...}），且首块起点即未对齐。

## 错误签名

```text
pool malloc(3) misaligned or NULL: 0x5a68a6c411   (mod16=1)
pool malloc(8) misaligned or NULL: 0x5a68a6c418
OHOS pool alignment test FAILED (rc=1)
```

## 根因

上游 `cc_dynamic_pool_malloc` 的对齐实现：

```c
size_t padding = 0;
if (!pool->is_packed) {
    padding = size % pool->alignment_boundary;   /* 仅追加 size%boundary 字节 */
}
pool->free_ptr = ptr + size + padding;
```

`size % boundary` 只在“当前 size 恰为 boundary 倍数”时才把 free_ptr 留在边界上；
对任意 size 无法保证下一块对齐。且 `cc_dynamic_pool_new_conf` 建池时
`free_ptr = page + sizeof(PageInfo)` 未做首块对齐。这是**库内算法缺陷，与平台无关**
——OHOS libc malloc 探针实测 16 字节对齐良好（`malloc(16) -> mod16=0`）。

## 修复

`patches/0001-src-memory-cc_dynamic_pool.c.patch`：
1. 建池：`!is_packed && boundary>1` 时把 `free_ptr` 圆整到 `alignment_boundary`；
2. 分配：`padding = boundary - ((uintptr_t)(ptr+size) % boundary) % boundary`，
   每块后 free_ptr 仍落在边界上。

## 验证

- `test_ohos_adapt.c` pool_alignment_test：boundary=16、9 种尺寸全对齐，PASS；
- 上游 16 个测试可执行 249/249 用例通过（无回归）；
- consumer 冒烟 `size=3 elem=2` 通过。

## 适用边界

- 仅非 packed（`is_packed=false`）且 `alignment_boundary>1` 的池受影响；
  默认 packed 池（boundary=1）行为不变；
- 需要对齐契约的下游：SIMD 加载、max_align_t/atomic 类型、外部 ABI。

## 查重差异

- 与 **E476**（foonathan/memory，OHOS musl 小对象 malloc 仅 8 字节对齐 + posix_memalign
  修复）不同：E476 是平台 libc 对齐契约问题；本条目是库内 padding 算法缺陷，与平台无关，
  解决方案为源码头文件内圆整 free_ptr。trigger（alignment 关键词）部分重叠，根因/方案不同。
- 与 **E092**（cmake 不识别 OHOS）无直接关系。