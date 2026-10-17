# 适配笔记 — astronomical-almanac 5.6

## 概述

Astronomical Almanac 5.6 是美国海军天文台 (USNO) 的天文年历计算程序，由 S. L. Moshier 编写。
实现了基于《The Astronomical Almanac》(1986) 的行星位置、太阳/月亮历表、坐标变换、章动、岁差、大气折射等计算。

## 源码

- 仓库：https://github.com/DouglasAllen/clib-astronomical-almanac-5.6
- 原始 tarball：`astronomical-almanac_5.6.orig.tar.gz`
- 主要作者：S. L. Moshier (1987-2006)
- 许可：Public Domain (U.S. Government work)

## 构建系统

- 纯 Makefile，无 configure 脚本
- 默认使用 gcc，需要通过 make CC=... 覆盖
- 无 install 目标，需要补丁添加
- 仅依赖 `-lm`（标准数学库）

## 产出物

命令行工具：
- `aa` — 主天文计算程序（交互式）
- `conjunct` — 行星合计算
- `moonrise` — 月出月落计算

数据文件：
- `aa.ini` — 观测者初始参数（经纬度、气压等）
- `star.cat` — 恒星目录
- `messier.cat` — 梅西耶天体目录
- `orbit.cat` — 轨道目录

## 适配要点

1. **补丁**：添加 install 目标到 Makefile
2. **编译器覆盖**：通过 make CC=$CC 传递
3. **平台检测**：仅支持 Linux/OHOS
4. **交互式程序**：aa 是交互式程序，测试需要 pipe 输入

## 已知限制

- 上游源码较老（1998-2006），不再维护
- 原始下载链接 (waterlan.home.xs4all.nl) 已失效，使用 GitHub 镜像
- 交互式界面，无命令行参数模式

## W0 依赖检查

无外部依赖，仅需标准 C 库和 libm。
