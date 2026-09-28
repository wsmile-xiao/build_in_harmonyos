# DRAFT：OpenBLAS/LAPACK >= 3.10 头文件与 CLAPACK 风格调用原型冲突

> Status: **Draft**（待审核 promote）| severity: `P1` | category: `dependency` | Updated: 2026-09-26
> 对应: `knowledge/drafts/DRAFT-ohos-openblas-lapack310-clapack-prototype-conflict.kv`
> 来源: kaldi g20231112 适配（feat/kaldi-g20231112，依赖 openblas/0.3.34）

---

**匹配关键词**：lapack.h, lapacke.h, LAPACK_FORTRAN_STRLEN_END, CLAPACK, clapack.h, f2c.h, cblas-wrappers, stptri_, sgetrf_, OpenBLAS, no matching function for call to

## 错误签名（error_signature）

```text
no matching function for call to .s?[dt][gp]e?[ts][rv][fi]_|lapack.h.*FORTRAN_STRLEN|cblas-wrappers
```

## 错误摘录（error_excerpt）

```text
../matrix/cblas-wrappers.h:386:3: error: no matching function for call to 'stptri_'
  stptri_(const_cast<char *>("U"), const_cast<char *>("N"), num_rows, Mdata, result);
/.../include/lapack.h:21346:6: note: candidate function not viable: requires 7 arguments, but 5 were provided
```

## 根因（root_cause）

OpenBLAS 安装目录里的 `include/lapack.h`（LAPACK >= 3.10）第 21 行**无条件** `#define
LAPACK_FORTRAN_STRLEN_END`，于是所有 Fortran 例程声明都追加 2 个隐藏字符串长度参数：

```c
#define LAPACK_stptri_base LAPACK_GLOBAL(stptri, STPTRI)
void LAPACK_stptri_base(char const* uplo, char const* diag, lapack_int const* n,
                        float* AP, lapack_int* info, FORTRAN_STRLEN, FORTRAN_STRLEN);
```

而按 CLAPACK/f2c 风格写的消费方代码是 5 参纯指针调用，签名不匹配；
编译器随后把整段 CLAPACK 包装函数判为非法，连带报出 `sgetrf_/sgesvd_/ssptrf_/ssptri_`
等一系列“独立”错误，容易被误判成多处理解。

## 推荐处置（rec_approach）

不要逐个例程去改调用（改动面大、还要求 `FORTRAN_STRLEN` 语义正确）；
改**声明来源**：在消费方基础头（kaldi：`src/matrix/kaldi-blas.h`）的 `HAVE_OPENBLAS`
分支不再包含 `lapacke.h`（它间接拉入 `lapack.h`），改为包含随源码自带的 CLAPACK 原型头：

```cpp
#include "cblas.h"                 // OpenBLAS 的 CBLAS 头
#include "../../tools/CLAPACK/f2c.h"
#include "../../tools/CLAPACK/clapack.h"   // 5 参指针原型，与 CLAPACK 风格调用一致
```

注意保留该分支原有的 `#undef abs/dabs/min/max/complex` 等清理。
另一条路是改用 `LAPACKE_*` 接口，但涉及列主序/返回值语义变化，改动面大。

## 影响面（可复用性）

所有“用 CLAPACK/f2c 原型调用 LAPACK 例程、但链接的是 OpenBLAS”的库（kaldi 系、部分数值库）
在 OpenBLAS >= 0.3.2x（内含 LAPACK >= 3.10 头）下都会命中；旧 OpenBLAS（LAPACK <= 3.9）无此问题，
所以表现为“升级 OpenBLAS 后突然大量链接/编译错误”。

## 验证

kaldi g20231112：`patches/0003-openblas-lapack-headers.patch` 后 `kaldi-matrix` 等编译通过，
`matrix-lib-test`、`sp-matrix-test` 等上游测试 123/123 通过。
