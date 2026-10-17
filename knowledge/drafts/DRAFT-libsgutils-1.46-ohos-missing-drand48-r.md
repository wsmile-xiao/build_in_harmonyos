# DRAFT-libsgutils-1.46-ohos-missing-drand48-r：OHOS libc 缺 glibc 可重入随机函数族

> Contributor: pc1-40 | Status: Draft | Updated: 2026-09-16
> Source: libsgutils (sg3_utils) 1.46 适配（task libsgutils-1.46-r01-pc1-40-20260916T131204Z）

## 问题

HarmonyOS PC（OHOS libc，musl 系）在编译使用 **glibc 可重入随机函数族**的上游
源码时报错，典型形态：

```text
sg_dd.c:179:28: error: tentative definition has type 'struct drand48_data' that is never completed
static struct drand48_data drand;/* opaque, used by srand48_r and mrand48_r */
sg_dd.c:2404:25: warning: call to undeclared function 'mrand48_r'; ISO C99 and later do not support implicit function declarations
```

即：`struct drand48_data` 类型、`srand48_r()`、`mrand48_r()` 在 OHOS libc 中
不存在。POSIX 基础族 `srand48/mrand48/drand48` 可用（实测编译通过）。

## 根因

`drand48_data` 与 `srand48_r/mrand48_r` 是 glibc 扩展（可重入变体），不属于
POSIX 必选集。OHOS libc（musl 系）只提供 POSIX 基础族，不提供 _r 变体与
opaque 状态结构体。

## 方案（两级替换）

**情形 1：单线程路径** —— 直接降级为全局非可重入版本：

```c
/* before */
static struct drand48_data drand;
srand48_r(seed, &drand);
...
mrand48_r(&drand, &rn);
/* after */
srand48(seed);
...
rn = mrand48();
```

**情形 2：多线程路径（per-worker 状态）** —— 必须保持每线程独立状态，不能共
用全局 srand48/mrand48。将 opaque 状态字段替换为 `uint64_t rng_state`，用
xorshift64 生成伪随机序列：

```c
/* Rq_elem 内 */
long seed;
uint64_t rng_state;                 /* replaces struct drand48_data */

/* 初始化（每个 rep/worker 独立 seed） */
rep->rng_state = (uint64_t)rep->seed;

/* 取值 */
rep->rng_state ^= rep->rng_state << 13;
rep->rng_state ^= rep->rng_state >> 7;
rep->rng_state ^= rep->rng_state << 17;
rn = (long)(rep->rng_state & 0xffffffffU);
```

注意：绝不可在多线程中共用全局 srand48/mrand48 状态（数据竞争）。

## 验证

- libsgutils (sg3_utils) 1.46：sg_dd.c / sgh_dd.cpp / sg_mrq_dd.cpp 应用上述
  补丁后全库 `make` 通过；`sgs_dd if=... of=... bs=512 count=4` 文件模式运行
  rc=0；testing/ 17 个独立可执行用例全部构建成功。
- 补丁文件：archives/l/libsgutils/1.46/patches/0004-src-sg_dd.c.patch、
  0006-testing-sg_mrq_dd.cpp.patch、0007-testing-sgh_dd.cpp.patch。

## 适用边界 / 反例

- 仅影响使用 glibc _r 随机族的上游库；只使用 POSIX 基础族（srand48/mrand48/
  drand48）的库无需任何改动。
- xorshift64 与 mrand48 的分布不同（mrand48 输出 [-2^31, 2^31)，xorshift64 取
  低 32 位为 [0, 2^32)），仅适合测试数据填充等无业务分布要求的场景；若业务依赖
  特定分布，须另选等价 PRNG。
- 单线程工具可简单降级；多线程必须 per-rep 状态。

## 查重差异（对既有知识）

- 既有 `knowledge/musl-glibc-full-comparison-iso-posix.md` 只覆盖 POSIX
  drand48 基础族（标注 ✅），未覆盖 glibc _r 变体缺失。
- knowledge/graph 与 knowledge/drafts 均无 drand48_data/srand48_r/mrand48_r
  条目（四范围查重未命中）。
- 相关条目：DRAFT-oatpp-1.3.1-ohos-libatomic-version-subdir（同族：OHOS libc
  缺失工具链/glibc 构件，替换方案模式通用）；E011（HMDFS/OHOS 平台 libc 差异族）。
