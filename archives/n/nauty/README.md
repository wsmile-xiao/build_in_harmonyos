# nauty

nauty（No AUTomorphisms, Yes?）是一个用于计算图和有向图自同构群的程序，还可以生成规范标号。

## 可用版本

- 2.9.3（已发布）

## 软件描述

nauty 计算图的自同构群和规范形式。它包含以下工具：
- dreadnaut：交互式命令行界面
- geng：生成给定阶数的所有图
- genbg：生成所有二部图
- shortg：计算规范形式
- labelg：计算规范标号
- 多种库变体（libnauty、libnautyS、libnautyW、libnautyL、libnautyQ）

## 主页

https://pallini.di.uniroma1.it/

---

## 补充：鸿蒙 PC conan 配方（2026-08-17）

# nauty

**nauty & Traces — 图同构与图生成工具集 — geng/genbg 枚举图、labelg 规范标号、shortg 去重等 50 余个命令**

## 命令行工具

- `geng`
- `genbg`
- `labelg`
- `shortg`
- `dreadnaut`
- `amtog`
- `complg`
- `converseg`

## 库

- `libnauty.so`

## 构建

- 构建系统：autotools
- 许可证：Apache-2.0
- 上游：https://pallini.di.uniroma1.it/

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 2.9.3 | built | 首个鸿蒙 PC conan 配方 |

## 为什么做这个包

passagemath（SageMath 的模块化重打包）在鸿蒙 PC 上的 wheel 需要它作为原生底座。

