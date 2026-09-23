# DRAFT-oaknut-jit-assembler-pure-encoding-assertion - JIT/汇编器库纯编码断言验证

> **Contributor**: codex | **Status**: VERIFIED DRAFT | **Updated**: 2026-09-17
> **Source event**: oaknut 1.2.2-git20240301.94c726c HarmonyOS PC 适配

## 知识类型与提升边界

本条目是路径 B 知识库扩展候选，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote 或已获 B 类认定；是否提升及最终分类由知识库维护者和赛事评审决定。

新增点仅是"汇编器/JIT 库在不执行机器码的前提下做确定性消费者验证"的闭环。OHOS 的
W^X（E045）、ELF 签名（E077）、header-only C++20 配方（cxx_std_20 + cppstd 提升）均为
既有方法，不在本条目中重复申报。

## 适用场景

本方法适用于同时满足以下条件的 header-only 汇编器/代码发射器库：

- 核心能力是动态生成目标架构机器码（AArch64/x86 等），而非普通算法库；
- 上游测试几乎全部依赖执行生成的机器码（mmap RWX 可执行内存）；
- 上游测试框架（Catch2 3 等）未发布到制品仓，或目标架构不可用；
- 需要一种确定性强、跨架构可移植、无 JIT 无框架的消费者验证。

普通 C/C++ 库仍应采用编译、链接和运行消费者程序的方式。目标真机可用且测试框架已发布
时，仍应补充 JIT 执行子集（见 fallback），本方法不能替代它。

## 问题模型

汇编器库横跨"编译期编码"与"运行期执行"两个边界：

1. 上游测试用 `CodeBlock`（mmap RWX）执行生成的机器码，验证"编码 → 执行"全链路；
2. 在 OHOS 上，mmap RWX 受 W^X 策略（E045）影响，非 ARM 环境无法执行 AArch64 代码；
3. 上游测试框架 Catch2 3 可能未发布，`find_package(Catch2 3)` 直接失败。

照搬上游测试会三面受阻。但汇编器的**编码正确性**本身是纯位运算，不依赖执行——只需
验证"emit 出来的机器码字节对不对"，而不必执行它。

## 推荐方法

### 1. 用非执行模式发射指令

`CodeGenerator{&uint32_t}` 把单条指令写入一个 32 位整数；`VectorCodeGenerator{&vec}`
把多条指令追加到 `std::vector<std::uint32_t>`。两者都不调用 mmap、不执行代码。

### 2. 断言机器码与已知编码向量一致

编码向量来源优先级：

1. 上游测试的 `T(HEX, CMD)` 宏向量（如 `tests/general.cpp`、`tests/basic.cpp`），
   这些是上游在真实环境验证过的确定性值；
2. 源码 `emit<"0101001010h..."...>` 模板手工推导；
3. ⚠️ **不要盲信 README 示例**：oaknut README 写 `MOV(W0,42)` 输出 `0xd2800540`，
   实为 64 位 `MOVZ X0`（sf=1）；正确 32 位 `MOVZ W0` 是 `0x52800540`（sf=0）。
   README 把两种位宽编码写混，照抄会得到错误期望值。

### 3. 覆盖多种指令类别 + 边界编码

单指令（MOV/RET/ADC/ADD/AND）+ 页偏移（`PageOffset<21,12>::encode`）+ 多指令发射
（VectorCodeGenerator）。页偏移编码是纯位运算，天然无 JIT，可直接复用上游向量。

### 4. 让 CI 的破坏性反向验证（L1e）兜底

Shadow CI 移走包内 `lib/`/`include/` 后重跑 test_package，必须失败。这证明 test 真的
依赖被测包，而不是碰巧通过。

## 与已有知识的差异

- E045 处理 JIT 运行时的 mmap RWX/W^X 崩溃；本条目规避 JIT 执行，用编码断言验证，
  时间边界和目的都不同。
- E016 处理汇编器编译期"unknown instruction"；本条目处理消费者层的编码正确性验证。
- E310 处理 JIT smoke 的假失败；本条目主动不进入 JIT smoke，改用确定性编码断言。

## 禁止做法

- 不要在非目标架构或 W^X 受限环境执行生成的机器码。
- 不要照抄 README 示例的编码字面量作为断言期望值。
- 不要用 printf/pass 空壳测试顶替编码断言（R34）。
- 不要把 W^X、ELF 签名、C++20 配方等既有方法重复申报为本条目的创新点。
- 不要把"编码正确"写成"JIT 执行已验证"。

## oaknut 1.2.2-git20240301.94c726c 验证证据

真机单包 Shadow CI
`codex-1.2.2-git20240301.94c726c-oaknut-1.2.2-git20240301.94c726c-shadow-20260917-conan-20260917-093845-23949`
已通过：

- conan create passed, exit code 0；
- L0=pass、L1=pass（含 L1e 破坏性反向验证）、L4=pass、L5=pass、L2=skip（无 bin/）；
- test_package 13/13 断言通过（单指令编码 5 + PageOffset 5 + 多指令发射 3）；
- 上游 Catch2 3 测试因依赖缺失未执行，真实记录为未执行，未计为 PASS。

复现入口：

```sh
CI_PACKAGES="archives/o/oaknut/1.2.2-git20240301.94c726c" zsh ci/conan/build_and_test.sh
```
