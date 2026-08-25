# DRAFT-ohos-missing-awk-variant-supply：OHOS 缺 awk 变体（nawk/mawk）→ 下载编译补齐（缺环境就下，非系统性阻塞必须跑起来）

> Contributor: blesh-0.4.0-git20250806.8060b7a 适配 | Status: Draft | Updated: 2026-08-24
> Source: archives/b/blesh/0.4.0-git20250806.8060b7a（make check 实测 + onetrueawk 下载编译集成）

## 现象

ble.sh 上游测试 `ble/util` 系列循环遍历 awk/nawk/mawk/gawk 四种 awk 变体
（6 个控制字符用例 × 4 变体）。OHOS 只有 busybox awk 与 gawk——缺
**nawk**（The One True AWK）与 **mawk**，对应 12 项用例被测试框架 skip
（声明数 7897 与实跑数 7830 的差距之一）。

按"上游测试能跑都跑、缺环境就下"原则，nawk/mawk 是工具类依赖（可安装
补齐，非系统级阻塞），不能直接跳过——需下载编译补齐。

## 主从根因

- **主根因**：OHOS 缺 nawk/mawk awk 变体（平台工具链缺口，非系统性阻塞
  可补齐——工具类依赖可安装）。
- **附加 note（编译细节）**：
  1. onetrueawk tarball 不含 `awkgram.tab.c/h`（bison 生成物）——需先
     `bison -d awkgram.y` 生成（OHOS 有 bison）。
  2. `./maketab awkgram.tab.h > proctab.c` 生成 proctab.c。
  3. 链接需包含 `awkgram.tab.o`（否则 yyparse/arglist 未定义符号）。
  4. codeload URL 无 `.tar.gz` 扩展名——conan `get()` 按扩展名误判 zip
     （BadZipFile）——显式 `filename=` 指定（bash-git-prompt 同款教训）。
  5. 绕 configure：OHOS 沙箱 configure 临时目录权限受限——直接 clang
     编译 maketab + 各 .c → .o + 链接（不用 configure 生成路径）。

## 与现有知识的关系

- knowledge/graph 无 awk 变体补齐主题——本主题无覆盖。
- 跨库可复用：任何测试框架遍历多 awk 实现变体的库（ble.sh、awk 批处理
  工具链）在 OHOS 都会命中；"缺环境就下 + 绕 configure 直编"方法论
  适用于其他纯 C 工具补齐。

## 方案

1. conandata.yml 增加 `nawk_source`（onetrueawk/awk 上游 codeload URL +
   sha256）。
2. build() 中：bison 生成 awkgram.tab → maketab（HOSTCC clang）→
   `./maketab awkgram.tab.h > proctab.c` → 各 .c → .o → clang 链接
   （含 awkgram.tab.o）→ 输出 `nawk_bin/nawk`。
3. 测试时把 `nawk_bin` 放 PATH（`PATH=...:$PATH`），ble.sh 测试遍历
   到 nawk 变体即真实运行。
4. mawk 编译受阻于 configure 临时目录权限（OHOS 沙箱限制）——如实记录
   6 项仍 skip，不伪造通过率。

## 验证证据

- 本地 OHOS 环境 make check：nawk 集成后 util 6 项跑起来，7830/7830
  全过（100%）。
- manifest 申报：runnable 7824→7830、pass_rate `7830/7897（99.15%）`；
  67 项 skip 逐类如实分类（canvas 57 contra/X11 系统级 + util 6 mawk
  沙箱编译受阻 + bash 4 版本分支）。

## 适用场景

- 测试遍历多 awk 实现变体的库在 OHOS 上的适配。
- 任何缺工具类依赖（awk 变体/bison 生成物）时"下载编译补齐"的配方。

## 禁止做法

- 不要因缺 nawk/mawk 直接声明 skip 冒充"上游如此"——工具类依赖可安装
  （缺环境就下），非系统性阻塞必须跑起来；只有系统级阻塞（如 OHOS 无
  X11 图形栈）才可记录未运行。
- 不要伪造通过率——mawk 编译受阻（沙箱 configure 权限）如实记录 6 项
  skip，不与 nawk 混为一谈。
