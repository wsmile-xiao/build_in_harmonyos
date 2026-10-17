# lbfgspp 0.4.0 适配笔记

## 上游信息

- **项目**: LBFGS++ — header-only C++ L-BFGS / L-BFGS-B optimization library
- **作者**: Yixuan Qiu
- **GitHub**: https://github.com/yixuan/LBFGSpp
- **Tag**: v0.4.0 (commit c524a407fb85b74807f53de5a3ca2ddbcc164e54)
- **发布日期**: 2025-04-20
- **License**: MIT (LICENSE.md)
- **Homepage**: https://lbfgspp.statr.me/

## 源码验证

- **URL**: https://github.com/yixuan/LBFGSpp/archive/refs/tags/v0.4.0.tar.gz
- **SHA256**: 39c4aaebd8b94ccdc98191d51913a31cddd618cc0869d99f07a4b6da83ca6254
- **下载验证**: curl 下载后 sha256sum 匹配

## 包特性

- **package_type**: header-library (纯 header-only)
- **无编译**: package() 仅复制头文件 + LICENSE，不生成 .a/.so
- **依赖**: eigen/3.4.0 (header-only，已在制品仓 ohpcd)
- **C++ 标准**: C++11 (OHOS profile cppstd=17 兼容)

## 头文件结构

```
include/
  LBFGS.h          — L-BFGS solver (unconstrained)
  LBFGSB.h         — L-BFGS-B solver (box-constrained)
  LBFGSpp/
    BFGSMat.h
    BKLDLT.h
    Cauchy.h
    LineSearchBacktracking.h
    LineSearchBracketing.h
    LineSearchMoreThuente.h
    LineSearchNocedalWright.h
    Param.h
    SubspaceMin.h
```

用户通过 `#include <LBFGS.h>` 或 `#include <LBFGSB.h>` 使用。

## 上游测试

上游无正式测试套件 (无 make check / ctest)。`examples/` 目录包含:
- example-rosenbrock.cpp — Rosenbrock 函数优化示例
- example-quadratic.cpp — 二次函数优化示例
- example-rosenbrock-box.cpp — 盒约束优化示例
- example-rosenbrock-bracketing.cpp — Bracketing 线搜索示例
- example-rosenbrock-comparison.cpp — 线搜索算法比较

examples 仅打印结果，无断言。test_package 提供带收敛性验证的真实测试。
