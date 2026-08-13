# mpfi 1.5.2 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
MPFI（Multiple Precision Floating-point Interval）是 MPFR 之上的**任意精度区间运算**库。
是 SageMath / passagemath 的 `RealIntervalField` 后端。

## 关键适配

### gmp 版本冲突必须 force
本包要 `gmp/6.3.0.1`（开了 `--enable-cxx` 的那版），而依赖的 `mpfr/4.2.2.1`
自身钉着 `gmp/6.3.0`：

```
ERROR: Version conflict: Conflict between gmp/6.3.0 and gmp/6.3.0.1 in the graph.
Conflict originates from mpfr/4.2.2.1
```

只有 `self.requires("gmp/6.3.0.1", force=True)` 能压过传递依赖钉的版本。

### 源码地址
`checksums.ini` **没有给** `upstream_url`。实测 `gitlab.inria.fr/mpfi/mpfi/uploads/…`
是错的（下回来是 404 HTML 页，sha256 不符）。可用的是 SageMath 的上游镜像：
`https://mirrors.mit.edu/sage/spkg/upstream/mpfi/mpfi-1.5.2.tar.bz2`
（`mirror.sagemath.org` 的重定向器实测不可用）。sha256 已本地核对一致。

其余：删除 `lib/*.la`。

## 真机验证（2026-08-13，HarmonyOS PC MateBook）
用 **CI 的 profile、且保留环境 LDFLAGS** 跑 `conan create`，
test_package 3 条**真实计算断言**全绿：

```
mpfi: 2*3=[6,6]、[1,2]*[1,2]=[1,4]、[1,2]+[3,4]=[4,6] 全部通过
```

断言的是**区间的左右端点**（`mpfi_get_left` / `mpfi_get_right`），不是只看能否加载：

- 精确值退化区间：`2 × 3 = [6,6]`
- 区间乘法：`[1,2] × [1,2] = [1,4]`
- 区间加法：`[1,2] + [3,4] = [4,6]`

**区间上下界算错是这类库最典型的缺陷**，只验加载完全测不出来。
