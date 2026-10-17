# buckygen 1.1 适配笔记

## 软件简介
buckygen 是 Ghent University CAAGT（Gunnar Brinkmann / Jan Goedgebeur / Brendan McKay）开发的
高效生成非同构富勒烯（fullerene）的程序：所有顶点度为 5 或 6 的三角剖分（对偶为所有面是五边形或六边形的三次平面图），
也支持 IPR 富勒烯（无相邻五边形顶点）。

官方来源：http://caagt.ugent.be/buckygen/ （buckygen-1.1.zip，GPL-3.0）

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure / autotools / cmake）
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4（OHOS 工具链）
- 状态: published

## 编译步骤

```bash
# 解压 buckygen-1.1.zip 后直接 make：
CC=clang CFLAGS='-O3' make
# makefile 核心目标：${CC} $(CFLAGS) buckygen.c -o buckygen
# 注意：splay.c 通过 buckygen.c 中 #include "splay.c" 内嵌，无需单独编译
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | makefile 使用 ${CC} shell 环境变量 | 裸用环境变量违反 R33（release worker 上为空→静默失败） | 配方 build() 从 `self.conf.get("tools.build:compiler_executables")` 取 C 编译器传入 `make CC={cc}` |
| 2 | makefile 无 install 目标 | 上游只提供编译目标（all/prof/stats/clean） | package() 手动将 buckygen 二进制复制到 bin/ |
| 3 | C2x 无原型警告（new_splaynode/old_splaynode 等） | 上游声明 `void new_splaynode();`（零参数原型），后续定义带参数 | 非致命警告（-Wdeprecated-non-prototype），不阻塞构建 |
| 4 | init-build 误判构建系统为 autotools | build-context 模板无 makefile 检测 | 手工将 manifest.yaml build.system 修正为 makefile |

## 源码修改
无（patch 为空，直接官方源码构建）

## 依赖版本
无外部依赖（仅标准 C 库）

## 验证结果

```bash
# 冒烟：生成 24 顶点富勒烯计数
./buckygen 24 -u
# Number of fullerenes generated with 24 vertices: 89
# 89 fullerenes generated; cpu=0.02 sec

./buckygen 32 -u
# Number of fullerenes generated with 32 vertices: 1812

# 全量输出（ascii code）示例
./buckygen 24 -a | head
# 输出 89 行 24 顶点富勒烯 ascii code
```
---

**编译结束**: 2026-09-05 17:30
**最终状态**: built
