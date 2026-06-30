# mgis (MFrontGenericInterfaceSupport)

## 简介

mgis (MFront Generic Interface Support) 是一个提供工具（函数、类、绑定等）来处理使用MFront通用接口编写的行为的库。它是TFEL/MFront项目的配套支持库，为FEM/FFT求解器开发者提供便捷的材料行为集成接口。

## 功能概述

- **行为加载**: 加载MFront生成的材料行为库
- **状态管理**: MaterialStateManager和MaterialDataManager管理积分点状态
- **多语言绑定**: 支持C++、Python、C、Fortran等语言接口
- **FEniCS集成**: mgis.fenics模块支持FEniCS有限元求解器
- **保存/恢复**: HDF5支持的状态保存和恢复功能

## OHOS适配要点

1. **CMake配置**: 需要`-DUNIX=TRUE`和`-Denable-mgis-function=OFF`（C++20限制）
2. **TFEL依赖**: 必须先编译安装TFEL 5.2，cmake配置时指定`TFEL_DIR`
3. **Clang兼容**: 需要修复属性语法兼容问题（见补丁0002-0003）
4. **前向声明**: MaterialStateManager需要Context前向声明（见补丁0004）
5. **静态编译**: 推荐`-Denable-static=ON`

## 依赖关系

- **必需依赖**: TFEL >= 5.0
- **可选依赖**: HDF5（保存/恢复功能）、Boost.Python（Python绑定）

## 补丁说明

| 补丁 | 用途 |
|------|------|
| 0001-FindTFEL-add-dependencies.patch | 修复TFEL cmake包依赖查找，添加TFELSystem/TFELUtilities |
| 0002-Config-c-fix-clang-attributes.patch | 修复Clang 15属性语法兼容，使用C++11属性语法 |
| 0003-ErrorBacktrace-fix-attribute-order.patch | 调整属性顺序为`[[nodiscard]] MGIS_EXPORT` |
| 0004-MaterialStateManager-add-forward-declaration.patch | 添加Context前向声明 |

## 参考资料

- 官网: https://thelfer.github.io/mgis/web/index.html
- GitHub: https://github.com/thelfer/MFrontGenericInterfaceSupport
- JOSS论文: https://www.theoj.org/joss-papers/joss.02003/10.21105.joss.02003.pdf