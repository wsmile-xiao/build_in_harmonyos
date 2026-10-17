# libSEDML

libSEDML 是 SED-ML（Simulation Experiment Description Markup Language，仿真
实验描述标记语言）文件的 C++ 读写库，由 Devisor 生成并手工维护，复用
libSBML 的 XML 解析层。

## 功能概述

- 读写 SED-ML L1V3/L1V4/L1V5 文档（模型、仿真、任务、数据生成器、绘图）
- 文档级别/版本间转换与校验（错误日志分级）
- KiSAO 算法本体查询（编译进库，无需数据文件）
- NuML 数值结果文档支持（经 libNuML）

## OHOS 适配

- 依赖的 libSBML 5.21.0、libNuML 1.1.7、expat 2.7.1 尚未进入制品仓，当前配方
  从官方发布包静态编译这些依赖并随包交付；三者独立入仓后应改为常规
  `requires` 引用。
- 压缩文档读写（.gz/.zip/.bz2）暂未启用（`WITH_ZLIB=OFF`），纯 XML 读写不受影响。
- 默认静态交付；`shared=True` 可产出动态库（PIC + 重签名逻辑已就位）。

## 依赖关系

- 构建期（配方内静态编译）：expat 2.7.1、libSBML 5.21.0（core only）、
  libNuML 1.1.7，均为官方源。
- 消费者：仅需链接包内四个静态库（顺序 sedml → numl → sbml → expat）及系统
  libm，无其他 conan 依赖。

## 参考资料

- 上游仓库：https://github.com/fbergmann/libSEDML
- SED-ML 规范：https://sed-ml.org/
- libSBML：https://github.com/sbmlteam/libsbml
- libNuML：https://github.com/NuML/NuML
