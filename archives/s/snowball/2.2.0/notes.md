# snowball 2.2.0 适配笔记

> 适配日期: 2026-10-03 | 状态: built | 任务: #14770 (j669539)

## 软件概况

Snowball 是词干提取算法（stemming）的参考实现与开发语言：`algorithms/*.sbl` 用
Snowball 语言描述 29 种语言的词干算法，先用 C 编译出 snowball 编译器（自举），
再由它生成各语言算法的 C 源码，与 `runtime/`（api.c/utilities.c）一起归档为
`libstemmer.a`。对外 API 是单个自包含头文件 `include/libstemmer.h`
（零 `#include`、带 C++ guard），并提供 `stemwords` 命令行工具。

- 上游: https://github.com/snowballstem/snowball （v2.2.0, 2021-11-10 发布）
- 语言: 纯 C（BSD-3-Clause）
- 依赖: **零**（W0 核验：无 conan requires，系统 libc 即可）
- 构建系统: 单 GNUmakefile，无 configure

## 编译过程

1. 下载官方 tarball（CSV 批次实测 200 KB 级，SHA256 见 conandata.yml）
2. `make -j1 CC=clang AR=llvm-ar RANLIB=llvm-ranlib libstemmer.a stemwords`
3. `make -j1 ... check_stemtest`（自包含回归）
4. conan create 一次通过：零补丁、零平台 flag、零源码修改

### 关键点

| # | 要点 | 说明 |
|---|------|------|
| 1 | CC/AR/RANLIB 必须命令行注入 | GNUmakefile 不定义 CC 默认值；按 R33 从 Conan conf 取，禁裸 shell 变量 |
| 2 | perl 生成算法清单 | `algorithms.mk`、`libstemmer/libstemmer.c`、`modules.h` 由 `libstemmer/*.pl` 生成（env shebang `#!/usr/bin/env perl`）——ohos-aarch64 profile 的 buildenv PATH 已含 perl，无需额外处理 |
| 3 | R9 -j1 | HMDFS 并行 make 撞 jobserver fifo 风险，全链单作业 |
| 4 | 产物 = 静态库 + CLI | R26 默认静态（.a）；stemwords 装入 bin/ → 软件级 commands.json 声明（R38） |

## 上游测试与统计

上游 `make check` = **1 个自包含目标 + 48 个数据驱动目标 = 49 个注册目标**：

| 组 | 目标数 | 依赖 |
|----|--------|------|
| check_stemtest | 1（内嵌 8 用例：emoji 变位 / U+40079 / 数字损伤回归 #66 #81，后 6 例遍历 29 算法） | 无（tests/stemtest.c 自包含） |
| check_utf8_% | 29 | 外部 snowball-data 仓 |
| check_iso_8859_1_% | 16 | 同上（iconv 转码） |
| check_iso_8859_2_% | 2 | 同上 |
| check_koi8r_% | 1 | 同上 |

### 数据仓版本错配问题（本次适配的核心发现）

snowball-data 仓（~500MB）**无 tag**，main 分支随算法演进持续重新生成期望输出。
用 main HEAD 数据对 v2.2.0 算法跑 `make check`，28/48 目标 diff 失败——不是平台
问题，而是**数据版本错配**：例 danish 期望 `bbc's→bbc`（撇号规则是 v2.2.0 之后
的算法增强），v2.2.0 算法输出 `bbc's`。CI 通道用 main 数据会得出系统性假失败。

**解法**：锁定数据仓在 v2.2.0 发布日（2021-11-10）之前的最后提交
`0703f1d6a21802c3ff00c2c8b31bd255b74b2aec`（"Update german2 test data"）作为
数据快照。用该快照实测：**48/48 数据目标全过 + stemtest 全过，`make check`
整体 exit 0**。

### 数据快照获取通道经验

- git clone / tarball 整包下载在低速通道必断连（早 EOF / 截断）
- `raw.githubusercontent.com` 逐文件下载最稳：纯文本优先，仅 .gz 变体语言
  （arabic）回退 gz，**按行数（voc==output）与 `gzip -t` 校验防截断**——
  截断的期望文件会产生尾部整段缺失型 diff 假失败（swedish 实锤：14475 vs
  30623 行）

### 适配后测试统计（统计表口径）

| 组 | 注册目标 | 实跑 | 通过 | 说明 |
|----|---------|------|------|------|
| check_stemtest（自包含） | 1 | 1 | 1 | conanfile build() 内执行（CI 内可复现） |
| 数据驱动目标 | 48 | 48 | 48 | 适配机对 0703f1d6 快照实测全过（数据仓不入库，CI 无法复现，已如实标注） |
| 鸿蒙特有/消费者测试 | 1+1 | 2 | 2 | test_package：test_snowball（29 语言清单+别名+23 项期望+回归镜像+KOI8-R）+ stemwords CLI fixture 往返 |
| **合计** | **51** | **51** | **51** | 通过率 100% |

test_package 的全部词干期望值均由 v2.2.0 算法对发布日快照数据的实测输出锚定
（非手写猜测），并镜像了上游 stemtest 的 emoji/U+40079/数字回归用例。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | main HEAD 数据 28/48 目标 diff 失败 | 数据仓无 tag，main 随新版算法重生成，与 v2.2.0 错配 | 锁定发布日前快照 0703f1d6a218（见知识草稿 DRAFT-snowball-2.2.0-external-testdata-release-date-snapshot） |
| 2 | 数据文件下载截断产生假 diff | 低速通道大文件截断（swedish 期望文件半截） | voc/output 行数一致性校验 + gzip -t + 按行数重试 |
| 3 | git clone snowball-data 断连 | git 智能协议大包传输在低速通道不稳定 | raw.githubusercontent 逐文件下载（每文件独立重试） |

## 源码修改

**无**。零补丁、零源码修改、零平台 flag——纯 C 库在 OHOS arm64 上开箱即编。
所有适配动作都在配方层（CC/AR/RANLIB 注入、-j1、目标选择、测试集成）。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| 无外部依赖 | - | 系统 libc（构建期 perl 由 profile 环境提供） |

## 验证结果

- 编译状态: 通过（conan create 一次通过）
- 上游测试: 自包含 8/8 用例通过；数据驱动 48/48 目标通过（发布日快照）
- 消费者测试: test_package 全过（见 test-report 输出）
- make check 整体 exit 0（适配机，STEMMING_DATA=快照）
