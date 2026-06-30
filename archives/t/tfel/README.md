# TFEL/MFront

## 简介

TFEL (Transferable Finite Element Library) 是一个用于材料行为建模的代码生成工具。MFront是其核心组件，提供领域特定语言(DSL)用于定义材料属性、机械行为和模型。

## 功能概述

- **材料属性定义**: Young's模量、热导率等物理属性的计算函数
- **机械行为建模**: 弹塑性、蠕变、损伤等本构模型
- **求解器接口**: 支持Cast3M、Code-Aster、Abaqus、CalculiX等多种有限元求解器
- **通用接口**: 提供generic interface供其他求解器使用

## OHOS适配要点

1. **CMake配置**: 必须添加 `-DUNIX=TRUE` 以启用UNIX特定组件
2. **链接器**: 需要显式链接libc++和libc++abi
3. **静态编译**: 推荐 `BUILD_SHARED_LIBS=OFF` 提高稳定性
4. **禁用绑定**: Python/Fortran/Java绑定可禁用减少依赖复杂度

## 依赖关系

- **编译依赖**: CMake 3.16+, Clang编译器
- **可选依赖**: Python (绑定), Boost (测试)

## 参考资料**

- 官网: https://thelfer.github.io/tfel/web/index.html
- GitHub: https://github.com/thelfer/tfel