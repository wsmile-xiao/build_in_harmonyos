# E534 — LINPACK dqrdc/dqrsl 缺失：openblas/lapack 不含经典 LINPACK QR 例程

## 错误特征

链接 Fortran R 包转独立库时出现：

```
ld.lld: error: undefined symbol: dqrdc_
ld.lld: error: undefined symbol: dqrsl_
```

## 触发条件

- 构建系统: conan / 手动 flang+clang 链接
- 阶段: linking
- 前提: 源码调用了经典 LINPACK QR 例程 `dqrdc`/`dqrsl`
  （如 KernSmooth 的 blkest.f、cp.f），且不以 R 环境（R 内部自带 LINPACK）构建

## 根因分析

openblas 与 lapack Conan 制品只提供 BLAS + LAPACK 例程；经典 netlib LINPACK 的
`dqrdc_`/`dqrsl_`（QR 分解与 QR 最小二乘求解，Dongarra et al. 1978）不属于
BLAS/LAPACK API（LAPACK 只有 `dgeqrf`/`dgeqp3`，无 `dqrdc`/`dqrsl`）。
R 运行时在其内部 LINPACK 捆绑中自带这两个例程，因此 R 包在 R 下编译链接正常，
一旦脱离 R 独立构建即出现未定义符号。

## 解决方案

### 推荐方案

从 netlib.org 获取公共领域 LINPACK 源码 dqrdc.f / dqrsl.f，
以「新增文件」补丁（`new file mode 100644`）加入 src/，随包内其他
Fortran 源码一并编译（flang/gfortran 均可）。conandata.yml patches 支持
新增文件补丁（git diff --no-index 生成）。

### 禁止做法

- ❌ 指望 openblas/lapack 提供 dqrdc/dqrsl —— 实测均无
- ❌ 用 LAPACK dgeqrf 替代并改写调用点 —— 破坏上游算法语义且改动大
- ❌ 静默丢弃依赖 dqrdc/dqrsl 的源码文件 —— 功能不完整

## 验证

```bash
llvm-nm libopenblas.a 2>/dev/null | grep dqrdc_   # 空 = 确认缺失
# 链接时报 undefined symbol dqrdc_ 即触达本模式
# 修复后: 链接通过，blkest_/cp_ 可正常调用
```

## 关联条目

- 相关: E242（Fortran/module/compiler identity）、E109（Fortran 编译器缺失）
