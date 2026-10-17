# E674 LAPACK 数值断言的四个必错点：uplo 三角形只写一半 + dsyev 升序 + dpocon 要 Cholesky 因子 + dgesvd 降序

> 状态: Draft（待审核 promote）| 日期: 2026-09-28 首轮 / 2026-09-29 e2e 扩展
> 来源: feat/lapackpp-2024.10.26（test_package 首轮 18 断言挂 3 条；e2e 管线扩至 32 断言又踩 dpocon/dgesvd 两坑）
> 机器可读层: 同目录 `E674-lapack-triangle-untouched-half-and-dsyev-ascending-eigenvalue-order.kv`

## 现象

`lapackpp/2024.10.26` 的消费者测试首轮 18 条数值断言挂 3 条：

```
ok   potrf: info == 0
FAIL potrf: L·Lᵀ == A (3x3 SPD)
ok   trtri: info == 0
FAIL trtri: M·M⁻¹ == I (2x2)
ok   syev: info == 0
FAIL syev: eigenvalues == {1, 3} (LAPACK dsyev 升序)
```

三条 `info == 0` 全过 → **LAPACK 调用本身是对的**，失败的是回乘校验的数学假设。

后续把测试扩成端到端管线（potrf→posv→porfs→pocon→syev/gesvd 交叉验证）时又踩两坑：
`pocon` 断言 `0 < rcond ≤ 1` 失败（rcond>1）、gesvd/syev 交叉验证失败。

## 根因

### ① LAPACK 只写 uplo 指定的三角形，另一半保留原值

`potrf(Uplo::Lower)` / `trtri(Uplo::Lower, NonUnit)` 返回时，**严格上三角不被清零**，
保留的是调用前的原矩阵元素。于是按整块数组做 L·Lᵀ 回乘时，把原始矩阵的上三角
当成了 L 的元素算进去。

实测：对 A = [[4,1,0],[1,5,2],[0,2,6]]（对称）做 `potrf(Lower)`，返回后
`A[0+1*3]=1`、`A[1+2*3]=2` 仍是**原值**，而它们已不属于 L。

### ② `dsyev` 特征值按【升序】返回

LAPACK 文档规定 `dsyev`/`dsyevd` 的特征值按**升序**返回（`W[0] ≤ W[1] ≤ …`）。
社区常按 "eig/eigh 降序" 的直觉写降序断言 → 必假失败。

**交叉验证**（排除适配缺陷）：同一输入 [[2,1],[1,2]] 直连参考 `lapack/3.12.1` 的
`dsyev_`（自写 C 程序链接 `liblapack.a`）：

```
raw dsyev_ info=0  W = [1 3]      # 升序
raw dsyev_ (U) info=0  W = [1 3]  # 升序
```

lapackpp 的 `syev`（`src/syev.cc`）是 `dsyev` 的薄封装（两次调用：query + 真正执行），
**行为与后端一致** → 是断言写错，不是适配缺陷。若当时误判为"库有问题"而去改
包装层，会引入真实回归。

### ③ `dpocon` 的 A 入参必须是 Cholesky 因子，anorm 才是原阵

`pocon(Uplo, n, const A, lda, anorm, &rcond)` 的两个矩阵入参**来自不同的矩阵**：
`A` 必须是 dpotrf/dposv 的**分解输出**（Cholesky 因子），`anorm` 是**原阵**的
范数（`lansy` 对原阵求）。这是该例程最反直觉的设计。

实测：e2e 管线里把**原阵**传给 pocon 的 A（anorm 用 lansy(原阵)），得到
`rcond > 1`——物理上不可能的伪结果，断言 `0 < rcond ≤ 1` 失败；改传 `posv`
返回的分解缓冲后立即通过。同理 `porfs` 的 `A`/`AF` 双入参也是"原阵/因子"分离。

### ④ `dgesvd` 奇异值按【降序】返回，与 dsyev 正好相反

`dgesvd` 的奇异值 `S[0] ≥ S[1] ≥ …`（降序），而 `dsyev` 特征值升序。
用 SPD 矩阵做交叉验证（对称阵的奇异值 = 特征值的绝对值）时必须**反序对齐**：
`S[i] ↔ W[n-1-i]`，同下标直比必错位 → 假失败。

### 附带的第五个易错点：列主序三角阵构造

列主序（`A[i + j*lda]`）下 `{2,0,1,3}` 实际是**上**三角，`{2,1,0,3}` 才是下三角。
把上三角阵配 `Uplo::Lower` 传入，LAPACK 只反解对角、另一半留原值 —— 症状与 ①
完全相同但根因是入参构造错，容易误诊。

## 解法

1. **回乘前清零非 uplo 侧三角形**（或按下三角显式取值）：
   ```cpp
   for (int j = 0; j < n; ++j)
       for (int i = 0; i < j; ++i)
           A[ i + j*n ] = 0.0;      // 严格上三角
   ```
2. **syev 断言按升序写**：`W[0]≈min`、`W[1]≈max`；若想与顺序无关，断言
   `max(W)≈λmax && min(W)≈λmin`。
3. **pocon：A 传分解输出（AF），anorm 传 lansy(原阵)**；porfs 的 A/AF 同理
   分离，别共用一个缓冲。
4. **gesvd vs syev 交叉验证**：`|S[i] − W[n-1-i]| < tol·λmax`。
5. **列主序三角阵入参**：下三角用 `{2,1,0,3}` 配 `Uplo::Lower`；
   上三角用 `{2,0,1,3}` 配 `Uplo::Upper`。先确认再传。
6. **优先选与顺序/三角形无关的不变量**做断言：`L·Lᵀ==A`、`QᵀQ==I`、`M·M⁻¹==I`、
   `A·x−b` 残差 ≈ 0、`‖Av−λv‖≈0` —— 比"逐元素等于参考值"更稳、更抗实现差异。
   本包最终 32 条断言即全部采用不变量口径（potrf/gesv/getrf+getrs/trtri/
   geqrf+orgqr/syev/gesvd 七族 + posv/porfs/pocon/lansy 端到端管线）。

## 实测证据（lapackpp/2024.10.26，2026-09-28/29）

首轮修正后：`TOTAL assertions=18` / `ALL PASSED`。e2e 扩展（含 dpocon 因子
入参修正与 gesvd/syev 反序对齐）后：`TOTAL assertions=32` / `ALL PASSED`，
两轮完整 conan create 结果逐项一致（rc=0）。

## 禁止

- ❌ 不清零上三角就断言 `L·Lᵀ==A`（假失败，且易误判为库缺陷）。
- ❌ 按降序写 `syev` 特征值断言（假失败；若据此"修"包装层则引入真实回归）。
- ❌ 把原阵传给 `pocon` 的 A（伪 rcond，常 >1；若断言只查正性还会**假通过**，
  条件数估计完全失真）。
- ❌ gesvd 与 syev 同下标直比 `S[i]==W[i]`（降序 vs 升序必错位）。
- ❌ 把 `info == 0` 通过但数值断言失败当作"编译/链接问题"去查别处——先查
  **校验数学本身**。

## 对下游的直接复用

适用于所有为 BLAS/LAPACK 封装库（lapackpp、blaspp、lapacke、cblas、SLATE）
编写消费者测试、或用"回乘验证分解 / 多例程交叉验证"的场景。
