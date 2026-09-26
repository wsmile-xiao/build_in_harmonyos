# E740 — header-only 库上游测试面为"自研单翻译单元 unittest"时的 N 清点与集成范式（crcpp 1.2.1.0）

> Draft: `E740` — 与同名 `.kv` 成对
> 来源任务：crcpp 1.2.1.0（新适配，header-only）

## 基本信息

- **ID**: E740
- **严重度**: 2
- **类别**: testing / rule4-counting / header-only
- **触发工具**: conan | make | clang
- **阶段**: testing

## 错误特征（可被日志命中的形态）

```
Invalid CRC: "123456789"
CRC parameters: ...
Expected CRC: ...
Computed CRC: ...
```

以及口径类症状：**「实测 N > 声明 N」→ rule4 少报硬 FAIL**（本仓 pr-audit：
zfp 712>2、gperftools 53>29、taskflow 3246>2909 同类）。

## 触发条件

- 上游是 header-only 库，**没有 ctest / meson test / 测试框架**；
- 上游测试 = 单翻译单元自研程序（crcpp: `test/src/main.cpp`），测试用例由**宏**声明
  （`CRC_TEST`、`CRC_PARTIAL_BYTE_TEST`），宏在定义处展开成多条独立断言；
- 用例部分包在 `#ifdef CRCPP_INCLUDE_ESOTERIC_CRC_DEFINITIONS` 条件编译区；
- 程序**失败才打印**（stderr）并置 `returnCode=1`，全过时输出为空、rc=0
  ——没有任何 "N tests passed" 汇总行可对账。

## 根因分析

1. **四口径（源码宏 / 框架注册 / assertion / 消费者断言）不得混用**：按源码宏数
   申报（crcpp 62 个宏调用点）会与断言实测（242）差 180，判少报；
   候选数法必须取**最大口径**并把差额逐项归因。
2. **条件编译区使 N 随宏开关浮动**：esoteric 开 → 59×4 + 3×2 = 242；关 → 13×4 = 52。
   必须声明所用开关（上游 gcc Makefile 默认 `-DCRCPP_INCLUDE_ESOTERIC_CRC_DEFINITIONS`，
   上游 CI `make -C test/prj/gcc` 即此口径）。
3. **只看 rc=0 会假绿**：失败才打印的程序必须同时核"失败打印行计数 == 0"
   （以及编译/链接是否真正执行），否则程序提前退出也能拿到 rc=0。

## 解决方案

**主方案**: ifdef-aware-assertion-counting-plus-upstream-makefile-driver

1. **N 清点（ifdef 感知）**：解析 `#ifdef CRCPP_INCLUDE_ESOTERIC_CRC_DEFINITIONS`
   区段统计宏调用点 × 展开断言数；宏数与断言数分别登记，PR 首行写断言口径
   （最大候选），差额归因写说明。crcpp 实测：宏 62（59 CRC_TEST + 3 partial）
   → 断言 242。
2. **上游测试进 `build()` 且驱动上游原生入口**：在 build 目录复刻相对结构
   （`inc/`、`test/src/`、`test/prj/gcc/`），`make -C test/prj/gcc` 只覆盖
   `CXX=LINKER=<conf 的 clang++>`（设备无 g++，§W0 先例）与
   `LDFLAGS="-Wall -static-libstdc++"`（避免测试二进制依赖 libc++_shared.so
   搜索路径，同 boost1.84-contract/CTRE 坑）；测试源、宏、断言保持上游字节级不变。
3. **判绿双条件**：`rc == 0` ∧ stderr 无 `Invalid CRC` 行 ⇒ 242/242 通过；
   任一不满足即抛异常让 G2 拦下。
4. **消费者面独立计数**：`test_package` 断言交付头自报版本宏
   （`CRCPP_MAJOR/MINOR/PATCH/REVISION == 1.2.1.0`）+ 逐位/查表/续算/非 8 位
   输入计算值，证明"打包的头 = 被测的头"；该批计数进 PR「鸿蒙特有测试」行
   （≥1），**不进上游分母**。

## 复现命令（设备可直接执行）

```sh
cd $HOME/ws/worktrees/crcpp-1.2.1.0
conan create archives/c/crcpp/1.2.1.0 \
  -pr:h=$HOME/ws/worktrees/crcpp-1.2.1.0/ci/conan/profiles/ohos-aarch64 \
  -pr:b=$HOME/ws/worktrees/crcpp-1.2.1.0/ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

日志中核对：`[upstream-tests] 清点 … esoteric on 断言=242` 与
`[upstream-tests] RUN rc=0 … 242/242 断言通过` 两行。

## 推广价值

- 适用任一"自研单测试程序 + 宏展开 + 条件编译区"的 header-only / 小型库
  （无框架测试面的 N 清点是 rule4 的高发返工点）；
- 「失败才打印 ⇒ rc 与失败行计数双判绿」适用于所有无汇总行的自研测试程序；
- 「build() 复刻相对结构驱动上游 Makefile、只覆盖编译器名」避免改上游测试构建。
