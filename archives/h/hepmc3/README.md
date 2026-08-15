# HepMC3

## 简介

HepMC3 是高能物理 Monte Carlo 事件记录库的新一代实现。用于存储和操作高能物理模拟产生的事
件数据，支持多种序列化格式（ROOT、HEPEVT、LHEF 等）。

- **官网**：https://hepmc.hepforge.org/
- **源码**：https://gitlab.cern.ch/hepmc/HepMC3
- **许可证**：GPL-3.0-or-later
- **构建系统**：CMake

## OHOS 适配

- 零外部依赖（纯 C++ 标准库 + pthread），适配简洁
- CMake 构建，无补丁需求
- 禁用 ROOT I/O、外部接口（Pythia8/Photos/Tauola），仅编译核心库 + search 库
- 上游 13-14 个单元测试全部运行（ctest），6 个 ROOT/外部依赖测试豁免
- 库命名：静态库使用 `_static` 后缀（`libHepMC3_static.a` / `libHepMC3search_static.a`）

## 依赖

- 无 Conan 依赖（零依赖库）

## 功能验证

```bash
conan create archives/h/hepmc3/3.1.2 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```
