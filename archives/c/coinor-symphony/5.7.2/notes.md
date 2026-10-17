# coinor-symphony 5.7.2 适配笔记

## 编译环境
- 构建系统: autotools（顶层为 AC_COIN_MAIN_PACKAGEDIR 编排层，实际驱动子包 `SYMPHONY/configure`，autoconf 2.59）
- 编译日期: 2026-09-23
- 编译器: clang/clang++ 15（OHOS aarch64 工具链）
- 状态: built

## 编译步骤

1. **源与数据**：官方 tag 归档 `releases/5.7.2.tar.gz`（sha256 三处同源全等
   `0807187a…55da`，tag `380996ca28` git ls-remote 实证）；测试数据
   Data-Sample `releases/1.2.13.tar.gz`（`cb4c3713…06c9`，与 coinor-cbc/coin-osi
   同钉版）解到 `data-stage/Sample`。
2. **依赖**：coinutils/2.11.13、coin-or/0.108.12（Osi）、clp/1.17.10、
   cgl/0.60.10.1、zlib/1.3.1（五枚 ohpcd 全在档，双 profile
   `-pr:h/-pr:b` 绝对路径 `conan install --build=missing` rc=0）。四包
   `include/coin` 头文件在 generate() 合并成单一 staging（configure 的
   `--with-*-incdir` 只收单目录）。
3. **configure**（in-source，`SYMPHONY/` 内）：

   ```bash
   CONFIG_SHELL=/data/service/hnp/bin/bash CC=clang CXX=clang++ TMPDIR=<可写临时目录> \
   CFLAGS='-O3 -pipe -DNDEBUG' CXXFLAGS='-O3 -pipe -DNDEBUG' \
   ./configure --prefix=/ --build=aarch64-unknown-linux-gnu \
     --enable-static --disable-shared --disable-dependency-tracking \
     --with-coinutils-lib='<libCoinUtils.a> <libz.a> -lm' --with-coinutils-incdir='<coin-include>' \
     --with-osi-lib='<libOsi.a …>'        --with-osi-incdir='<coin-include>' \
     --with-clp-lib='<libOsiClp.a libClpSolver.a libClp.a …>' --with-clp-incdir='<coin-include>' \
     --with-cgl-lib='<libCgl.a libOsi.a libCoinUtils.a libz.a -lm>' --with-cgl-incdir='<coin-include>' \
     --with-ositests-lib='<libOsiCommonTests.a …>' --with-ositests-incdir='<coin-include>' \
     --with-sample-datadir='<data-stage/Sample>'
   ```

   - **flags 模式**：已发布依赖包 `prefix=/` 固化进 .pc、pkg-config 路径不可用；
     闭包链接串用**直接 .a 绝对路径**（依赖 .la 的 `libdir='//'` 会让 libtool 报
     "not a valid libtool archive"，coinor-cbc 探索轮实测的同款坑）。
   - **CFLAGS/CXXFLAGS 显式钉死** `-O3 -pipe -DNDEBUG`（R33/coinor 家族当日铁律）：
     = 本机原生探索 config.log:1047 实测基座；防 CI worker 泄漏 `-fPIC -O2`
     （无 `-DNDEBUG`）造成 `#ifdef NDEBUG` 编译期分叉（coinor-cbc !11827
     ositests Segfault 教训）。
   - `--build=aarch64-unknown-linux-gnu`：老 config.sub 无 musl 词表，
     `-musl` 实测 `Invalid configuration … machine 'aarch64-unknown-linux' not recognized`。
4. **HMDFS 修复（build() 内 seds，无源补丁）**：
   - 生成器 `configure` 先行四处替换：`umask 077 && mktemp -d -q "./confstatXXXXXX"`
     → `umask 022 && mkdir -p ./conftmp`；fallback `tmp=./confstat$$-$RANDOM`
     → `tmp=./conftmp`；`umask 077 && mkdir $tmp` → `umask 022 && mkdir -p $tmp`；
     残余 `umask 077` → `umask 022`。AC_OUTPUT 内联跑的与生成出的 `config.status`
     即同时继承；configure 之后对 `config.status` 幂等补一遍兜底。
   - 探索期复现证据：`explore-configure2.log` 逐字
     `./config.status: line 1057: ./confstatXXXXXX/out: Permission denied`
     （HMDFS 把 umask 077 目录按共享属主落成 2700），手工三轮
     `config-status-fix{,2,3}.log` 收敛、fix3 无错误收尾即修法实证
     （E114 / DRAFT-E678 同族正解，生成物不进 git ⇒ 免 refresh-patch 登记）。
   - shebang（`#! /bin/sh` → OHOS shell）与 config.guess HarmonyOS 分支按
     coinor-cbc 同款防御性保留（`--build` 显式给出时不会触发）。
5. **构建**：`MAKEFLAGS='' make -j1`（单线程规避 HMDFS libtool .lo 并发截断，
   设备边界 §一.7/§一.13）。
6. **测试**：运行前 binary-sign-tool 自签 `src/symphony`、`test/unitTest`、
   `test/punitTest`（否则加载器 EPERM），再 `make -j1 test`
   （= `cd test && ./unitTest -miplib3Dir= -mpsDir=<Sample>`）。
7. **安装**：`make install DESTDIR=<package_folder>` → `bin/symphony`、
   `lib/libSym.a`、`lib/libOsiSym.a`、`include/coin/*.hpp`、`*.pc`、
   `share/coin/doc/SYMPHONY/`、`licenses/LICENSE`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Invalid configuration 'aarch64-unknown-linux-musl': machine 'aarch64-unknown-linux' not recognized`（explore-configure.log） | 上游老 config.sub 无 musl 词表（`grep -c musl config.sub`=0），coinor-cbc 可用的 `-musl` 三元组在此不可用 | 改 `--build=aarch64-unknown-linux-gnu`（config.sub 认识；CONFIGURE_RC=0 实证） |
| 2 | `./config.status: … ./confstatXXXXXX/out: Permission denied`、`cannot create a temporary directory in .`、`mkdir: './conftmp': File exists`（探索三轮修复日志） | autoconf 2.59 生成器用 `umask 077 + mktemp ./confstatXXXXXX` 建临时目录，HMDFS 按共享属主落盘 2700 后 other 位无 w（E114/DRAFT-E678 同族）；第二轮 `mkdir` 无 `-p` 撞已存在目录 | configure 前生成器四处替换（022 + 固定 ./conftmp + mkdir -p），生成链继承；configure 后对 config.status 幂等兜底（`_fix_config_tmp_mechanism`）；不改上游源、不登记补丁 |
| 3 | CI 环境泄漏 `CFLAGS/CXXFLAGS='-fPIC -O2'`（无 -DNDEBUG）风险 | CI worker 进程环境泄漏（仓库 FAQ 记载值），profile 与 ci/ 脚本均不设置 | configure 调用处显式钉死 `CFLAGS/CXXFLAGS='-O3 -pipe -DNDEBUG'`（与设备验证基座同值，三方同源） |
| 4 | `-F model.lp` 报 `Coin6002E Unknown image` → `Errors in reading mps file` 退出 -122 | CLI 语义：`-F` 读 **MPS**、`-L` 读 **LP**（`-h` help 实测） | test_package 与一切 LP 驱动一律用 `-L`；此语义入 E692 草稿 |
| 5 | 依赖 `.la` `libdir='//'`（prefix=/ 固化）会让 libtool 报 "not a valid libtool archive" | 已发布包 .pc/.la 按构建机前缀固化 | 闭包一律**直接 .a 绝对路径**注入（不走 -L/-l），与上游 cgl.pc 写法一致 |

## 源码修改

无（`patches: {}`）：依赖注入与 HMDFS 修复全部在 conanfile.py `build()` 内完成，
均为构建期对生成物的修复，不改动上游源码文件。

## 依赖版本

| 依赖 | 版本 | 角色 |
|---|---|---|
| coinutils | 2.11.13 | CoinUtils 基础库（闭包底层） |
| coin-or（Osi） | 0.108.12 | Osi 接口 + OsiCommonTests（ositests 断言面） |
| clp | 1.17.10 | LP 求解（ClpSolver/OsiClp，`-D__OSI_CLP__`） |
| cgl | 0.60.10.1 | 割平面（Cgl） |
| zlib | 1.3.1 | 闭包底层（-lz） |
| Data-Sample（数据） | 1.2.13 | `--with-sample-datadir` 激活 COIN_HAS_SAMPLE 测试数据面 |

## 验证结果

```bash
# W0 生死关（w0/w0-checks.md 命令+rc 逐字）
git ls-remote --tags … releases/5.7.2        # 380996ca28… RC=0
conan install w0/depcheck --build=missing -pr:h=<abs> -pr:b=<abs>   # RC=0 5/5
grep <ISA 头|printf 钩子> w0/SYMPHONY-releases-5.7.2                 # RC=1 无命中

# 原生探索（断点遗产，$TASK_DIR 日志尾逐字）
CONFIGURE_RC=0  MAKE_RC=0  TEST_RC=0
# make test: Severity PASSED : 412 / ERROR : 0 / "All tests completed successfully"

# 采信轮 + test_package（收尾时以 reports/test-report.md 逐字为准）
sh tools/conan_verify_round.sh coinor-symphony 5.7.2 --repo "$TARGET_REPO" --task-dir "$TASK_DIR"
# test_package: symphony -L model.lp → Version 5.7.2 + Optimal + Solution Cost -11
```

（上游/消费者测试的完整四分项统计、非 PASS 技术原因与逐字证据见
`reports/test-report.md`——本文件不重复计数。）

## 注意事项

- 顶层 `configure` 只做子包编排，**不要**用它（多一层 autoconf 脆弱面）；
  配方直接驱动 `SYMPHONY/configure`（coinor-cbc 同款口径）。
- `make test` 只跑 `test` 目标（unitTest）；`fulltest` 要 svn 下载 miplib3
  （不可用）、`ptest/pfulltest` 是 PVM 并行面——三面未运行已在
  `test_package/MANIFEST.yml` 与 PR 正文如实单列。
- Netlib 面（`-testOsiSolverInterface` 扩展数据）未配置，上游自报
  `Skipped Testing of OsiSymSolverInterface on Netlib problems`。
- CLI：`-F` 读 MPS、`-L` 读 LP（格式错配以 `Errors in reading mps file`/-122 退出）。
- OHOS 一切 ELF 运行前须 binary-sign-tool 自签（加载器 EPERM）。
