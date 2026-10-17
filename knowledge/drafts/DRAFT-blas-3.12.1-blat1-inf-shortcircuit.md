# netlib BLAS 复数 blat1 测试驱动缺 `SNRM==ZNRM` 短路分支导致 Inf 用例误报 FAIL

> 软件：blas 3.12.1（netlib 参考 BLAS，LAPACK 3.12.1 发行中的 BLAS 组件）
> 门禁：conan create 上游测试（BLAS/TESTING，flang-ohos/20.1.0）
> 状态：DRAFT（草稿，待人工审核提升为 E 条目）

## 问题

上游 LAPACK 3.12.1 的 `BLAS/TESTING` 复数 level-1 测试驱动 `cblat1.f`/`zblat1.f`
在 conan create 上游测试阶段报告 `SCNRM2`/`DZNRM2` 共 **16+16=32 例 FAIL**，全部为
`test=NaN`，集中在 `IV= 9`（Inf 输入）用例：

```
SCNRM2: N=     1, INCX=  -2, IV= 9, IW= 1, test=            NaN
SCNRM2: N=     1, INCX=   1, IV= 9, IW= 1, test=            NaN
...（16 行 × cblat1 + 16 行 × zblat1）
```

同期 `sblat1.f`/`dblat1.f`（实数 level-1 驱动）全部 PASS，仅有复数版误报。

## 根因

`BLAS/TESTING` 的 blat1 驱动实现了 Algorithm 978（Anderson 2017, "Safe Scaling in
the Level 1 BLAS"）安全缩放参考计算，测试值 `VALUES(9) = SXVALS(V0,2) = HUGE**2`
在单精度下溢出为 `+Inf`。输入含 Inf 元素时，库函数正确返回 `Inf`
（`sqrt(huge²+9huge²)` 数学上溢出为 Inf，IEEE 语义正确），参考期望值 `ZNRM` 亦为
`Inf`。此时比较链应直接判相等通过；但复数版驱动的 TRAT 比较链为：

```fortran
IF ((SNRM.NE.SNRM).OR.(ZNRM.NE.ZNRM)) THEN
   ...
ELSE IF (ZNRM == ZERO) THEN
   TRAT = SNRM / ULP
ELSE
   TRAT = (ABS(SNRM-ZNRM) / ZNRM) / (TWO*REAL(N)*ULP)   ! (ABS(Inf-Inf)/Inf)=NaN
END IF
```

`SNRM=Inf, ZNRM=Inf` 时走到 ELSE 分支，`ABS(Inf-Inf)=NaN` → `TRAT=NaN` →
`TRAT.NE.TRAT` 恒真 → 误报 FAIL。**实数版驱动同位置有 `ELSE IF (SNRM == ZNRM)
THEN TRAT = ZERO` 短路分支**（`sblat1.f:1254`、`dblat1.f:1302`），复数版缺失
（`cblat1.f`/`zblat1.f` 对应位置无）——上下游测试驱动不对称。

## 修复

在 `cblat1.f`/`zblat1.f` 的 TRAT 比较链中，于 `ELSE IF (ZNRM == ZERO)` 之前补齐
与实数版一致的短路分支：

```fortran
ELSE IF (SNRM == ZNRM) THEN
   TRAT = ZERO
ELSE IF (ZNRM == ZERO) THEN
   TRAT = SNRM / ULP
```

- 补丁：`0001-BLAS-TESTING-cblat1.f.patch`、`0002-BLAS-TESTING-zblat1.f.patch`
- 最小复现实证：`SCNRM2(1, (huge, -3*huge)) = Inf`（库行为正确，非库缺陷）
- 修复后：TOTAL=246 PASS / 0 FAIL（32 例误报清零）

## 适用范围

- 以 flang（flang-ohos）或 gfortran 编译 netlib 参考 BLAS/LAPACK 并运行
  `BLAS/TESTING` 复数 blat1 驱动的场景
- 任何复用 Algorithm 978 safe-scaling 测试值（0/极小/ulp/1/1·ulp/大/极大/Inf/NaN）
  的上游测试驱动，若比较链缺失 `==` 短路分支且输入可含 Inf

## 边界与反例

- 仅针对 **Inf 输入下 `SNRM==ZNRM`（含两者均 Inf）** 的比较；NaN 用例走既有
  `(SNRM.NE.SNRM)` 分支，不受影响
- 库自身对 Inf 输入的行为是正确 IEEE 语义，不应视为库 bug 而"修复"库
- 若上游已修复（新版本驱动补齐该分支），无需再打补丁，diff 对齐即可

## 查重结论

四范围查重（index.tsv / doc/ / graph/ / drafts/）：
- E109（gfortran 缺失）、E242（Fortran .mod module ABI）、E306（C++ std::polar 负半径
  NaN）、E535（cgns ctest 上游测试）均**不覆盖**本模式
- `knowledge/drafts/` 无 blas/blat/nrm2/flang 相关草稿
- 结论：**new_draft**（查重未命中，存在可跨库复用的新增差异）

## 相关草稿

- `knowledge/drafts/DRAFT-blas-3.12.1-blat1-inf-shortcircuit.kv`（本条目 .kv 对）