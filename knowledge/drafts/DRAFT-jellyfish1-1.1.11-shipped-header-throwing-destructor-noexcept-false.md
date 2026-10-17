# DRAFT-jellyfish1-1.1.11-shipped-header-throwing-destructor-noexcept-false：抛出析构位于被交付的库头时，E543 的时代标准降档出路不可用，noexcept(false) 才是最小干预正解

> Status: Draft | Updated: 2026-09-25
> Source: jellyfish1 1.1.11 HarmonyOS PC 适配（B 机真机，第 2 轮 conan create 2026-09-25 07:20，补丁 0001）
> 对应：knowledge/drafts/DRAFT-jellyfish1-1.1.11-shipped-header-throwing-destructor-noexcept-false.kv
> 对照条目：knowledge/drafts/E543-draft-7707.md 与同名 .kv（**按文件名引用**，见「关联条目」里关于 E 号复用的说明）

## 错误特征

运行期（真机一手读数，`~/tmp/uc2/z33-jellyfish1/tc4-r2/tc4-r2.out`）：

```text
:23  libc++abi: terminating due to uncaught exception of type err_t: eraise from library side
:24  Signal 6 (core dumped)
:25  RC[unfixed.runstatic]=134
:40  libc++abi: terminating due to uncaught exception of type err_t: eraise from library side
:41  Signal 6 (core dumped)
:42  RC[unfixed.runshared]=134
:63  libc++abi: terminating due to uncaught exception of type SquareBinaryMatrix::SingularMatrix: Matrix is singular
```

编译期先兆（同一份探针，clang 15 开着默认告警即给）：

```text
:9   warning: '~raise_t' has a non-throwing exception specification but can still throw [-Wexceptions]
:12  note: destructor has a implicit non-throwing exception specification
```

稳定错误签名（与 `.kv` 的 `error_signature` **逐字同源**，这里按分支拆开列；
正则取自上述一手日志原文）：

```text
libc\+\+abi:\s+terminating due to uncaught exception of type [\w:]+
warning:\s+'~?[A-Za-z_]+' has a non-throwing exception specification but can still throw \[-Wexceptions\]
note:\s+destructor has a implicit non-throwing exception specification
```

（三个分支在 `.kv` 里以 `|` 连接为一条 `error_signature`；`Signal 6 (core dumped)`
与 `RC=134` 是伴随读数，不写进签名以免把任何 6 号崩溃都误判成本条。）

- **关键判别**：链接与编译全过，一走到库内错误分支就整进程 abort（RC=134 / Signal 6），
  且该分支的 `catch` 永远接不到——静态链与共享链两臂读数相同，所以与链接方式无关。
- 在包级上的宏观症状：上游 `make check` **打补丁前 19 项全红**
  （`~/tmp/uc2/z33-jellyfish1/probe-check.log:44`「19 of 19 tests failed」、
  `probe/src/test-suite.log:5` 同值）；打本条补丁后同一棵树为
  4 PASS + 15 FAIL + 1 SKIP（`probe5b-check.log` 判决行、汇总 `:39`）。
  两个口径是**基线 vs 交付轮**的关系，不是互相顶替的关系。

## 触发条件

- 构建系统：任意（问题在被包含的库头语义，与构建系统无关；本例 autotools + conan）
- 阶段：compile（`-Wexceptions` 先兆）/ testing / runtime（真正 abort 在运行期）
- 库形态：**被交付的库头**里存在「析构函数中 throw」的惯用法，且该惯用法是库的
  全部/主要错误上报路径（实例 `jellyfish/err.hpp:123` 的 `~raise_t()`，宏 `eraise` 全库使用）
- 工具链：以 C++11 及以后标准编译（本包 conan profile `compiler.cppstd=17`，
  clang 15.0.4 + libc++/libc++abi）
- 消费者侧触发概率不低时症状尤其隐蔽：本包 GF(2) 随机矩阵奇异率约 29%，
  上游 `tests/generate_sequence.cc` 的 `catch(SquareBinaryMatrix::SingularMatrix)`
  重试循环因析构隐式 `noexcept` 永远接不到，第一轮撞上就 abort

## 根因分析

C++11 [class.dtor] 把析构函数的隐式异常规范从「可抛任何异常」改为**隐式 noexcept**，
从中 `throw` 离开析构即 `std::terminate`。这一层机制 E543 已经写清楚
（`E543-draft-7707.md:35-38`），本条不重复解释，本条写的是 **locus 造成的分叉**：

1. E543 把 locus 划在「其测试**有意**验证析构抛异常」那一类
   （`E543-draft-7707.md:28-30`，libtut 的 `teardown_ex` 组、`warn` 结果类型正是为该
   场景设计）。本包的抛出点在**被安装、被消费者包含的库头**里，不是测试代码。
2. `E543-draft-7707.md:42-43` 断言「交付的库头文件在现代标准下正常（消费者代码不会
   故意从析构抛异常）」——本包该前提为假：消费者只要触发库内任一错误分支即
   `std::terminate`、RC=134（一手 `tc4-r2/tc4-r2.out:23-25` 静态、`:40-42` 共享；
   `:52`/`:60` 加 `noexcept(false)` 后均 RC=0）。
   这组双臂探针同时**否证**了「cross-DSO RTTI/typeinfo 不匹配」这个更省事的替代解释
   ——两种链法都是 134，与链接方式无关。
3. `E543-draft-7707.md:54-63` 的推荐解法（`-std=gnu++98` 重编上游套件、不改任何测试
   代码）在本包**不可用**：降档只作用于被重编的那批翻译单元，修不到交付给消费者的
   库头；而且同一条目 `:77-78` 自身禁止把 `gnu++98` 加进配方（惩罚所有现代消费者）。
   本臂**只用上面这两条独立成立的前提**：自带 googletest 不是第三条论据（曾有的另
   一种表述已被否证并撤下，撤下记录单点记在台账候选 1 的本臂）。一手事实是它在
   clang15 + libc++ 下因 `unit_tests/gtest/include/gtest/internal/gtest-port.h:504`
   走到 `#include <tr1/tuple>` 而编译失败（libc++ 无 TR1 兼容层，一手
   `gtest-probe/without.log:4`），处置是编译期宏 `-DGTEST_USE_OWN_TR1_TUPLE=1`
   （A/B：不带宏单编 RC=1、带宏 RC=0，**未关闭 unit_tests 层**：交付轮
   `reports/w3-local-ci.log:703` 真编 `libgtest_a-gtest-all.o`、`:710` `AR libgtest.a`、
   `:786 PASS: unit_tests/unit_tests.sh`）。该判定与 `-std` 无关（该分支条件是
   `GTEST_USE_OWN_TR1_TUPLE` / `GTEST_OS_SYMBIAN` / `__GNUC__`，且 vendored 头内
   `GTEST_LANG_CXX11` 全域 0 命中）⇒ 它与「降档不可用」是两条正交机制（见「同包不同面」）。
4. `E543-draft-7707.md:73-74` 与同名 `.kv:34-36`（`forbid_1`）的原文禁令限定在
   「给上游**测试**的析构打 `noexcept(false)` 补丁……套件本该用时代标准跑」。
   本包用的正是该形态，但落在这个禁令**前提不成立**的场合。

⇒ 新增价值一句话：E543 的 `noexcept(false)` 禁令需要**按 locus 收窄适用面**——
抛出析构位于测试套件时用时代标准重编（E543 原场景）；位于**被交付的库头**、
且降档标准被该条目自禁时，`noexcept(false)` 一行才是最小干预正解。

## 解决方案

给**被交付的库头**里那个抛出析构显式加 `noexcept(false)`，一行、一个补丁：

```cpp
// jellyfish/err.hpp:123（补丁 0001）
~raise_t() noexcept(false) { throw err_t(oss.str()); }
```

要点：

- 改库头而非测试代码 ⇒ 消费者路径与上游套件路径**同时**被修好；
- 不引入任何 `-std` 旗标 ⇒ 库与消费者都留在目标默认标准（c++17）；自带 gtest 的编译
  缺口由**另一条正交**的编译期宏 `-DGTEST_USE_OWN_TR1_TUPLE=1` 解决（一手
  `gtest-port.h:504` 的 `<tr1/tuple>`：不带宏 RC=1、带宏 RC=0），**不是** C++11
  门槛问题；
- 不动宏名、不动 `catch` 侧语义，只恢复「throw 离开析构可以传播」这一 C++03 时代
  实际依赖的行为；
- 补丁经 `conandata.yml` 登记 `patch_type: portability`，随 `export_sources()` +
  `apply_conandata_patches()` 分发。

**与 E543 的分叉点（必须随本条一起读）**：同一个 `noexcept(false)` 动作，
E543 判禁止、本条判推荐，差别只在**抛点的 locus** 与**降档出路是否可用**。
检索时两条都会命中，靠这两问二选一：抛点在不在被安装的头里？把套件拉回时代标准
能不能修到被交付的那部分？

## 禁止做法

- ❌ 照搬 E543 的 `forbid_1` 去禁止「库头里的抛出析构」加 `noexcept(false)`；
  也 ❌ 把本类型直接判成命中 E543 而不核 locus（本包上一版就是这么判的，据此升 create）。
- ❌ 把 `-std=gnu++98` 加进配方 cxxflags / 给整个包降标准——E543 `:77-78` 已禁，
  本包消费者路径按 `compiler.cppstd=17` 构建，降档会把它拉回老标准。⛔ 也不要把自带
  googletest 的编译缺口当成本条的理由（撤下记录见台账候选 1）：那个障碍是
  `<tr1/tuple>`（`gtest-port.h:504`，处置 `-DGTEST_USE_OWN_TR1_TUPLE=1`），与本条
  禁令的 `-std` 面正交。
- ❌ 据 `terminate` 判定该库在 OHOS 不可用，或把成因写成"平台缺陷"/"上游缺陷"：
  同一棵树在 C++03 语义下正常，加一行 `noexcept(false)` 后 RC=0，
  属可修的语言规则版本差异。
- ❌ 靠删除或跳过上游用例来让 `make check` 变绿。
- ❌ 把本包那 15 条 FAIL 也算成本条的成因——它们是 `tests/compat.sh` 对上游 baked md5
  的字节级基线比对，成因**未定性**（实测现象：逻辑计数与上游一致、含全量条目的
  `_0`/`histo`/`stats`/全量 dump 不复现；已排除页大小 4096、`__int128` 两条路、
  以及跨 DSO RTTI/typeinfo），与本条的抛出析构无关，须各自独立表述。

## 验证

```bash
# 1) 抛点在被安装的头里（不是只在 tests/ 下）
grep -rn 'raise_t\|eraise' <src>/jellyfish/err.hpp

# 2) 最小双臂探针（同机同工具链，只差 noexcept(false) 一处）
#    未修臂：静态 RC=134、共享 RC=134（两臂同值 ⇒ 否证 cross-DSO 假设）
#    修复臂：静态 RC=0、共享 RC=0，并打印 CAUGHT
# 3) 打补丁后 conan create 必须真跑上游 make check 并留下逐条判决行
```

真实证据（全部 B 机一手件）：

- `~/tmp/uc2/z33-jellyfish1/tc4-r2/tc4-r2.out`
  `:23-25` 静态 RC=134、`:40-42` 共享 RC=134、`:52`/`:60` 修复后 RC=0；
  `:9`/`:12` 为编译期 `-Wexceptions` 先兆
- 基线：`~/tmp/uc2/z33-jellyfish1/probe-check.log:44`「19 of 19 tests failed」
- 打 0001 后同一棵探测树：`probe5b-check.log` 判决行 4 PASS + 15 FAIL + 1 SKIP、
  汇总 `:39`、`probe5b-a.out:18 CHECK_RC=2`
- 交付轮 conan create：`archives/j/jellyfish1/1.1.11/reports/w3-local-ci.log`
  汇总 `:788`「15 of 19 tests failed」、PASS 判决行 `:767/:773/:783/:786`、
  `:800 UPSTREAM_MAKE_CHECK_RC=2`；同数字独立对照件
  `~/tmp/ch/home-z33-jellyfish1/p/b/jellye1d3de609d8b5/b/build-release/test-suite.log:5`
  「15 of 19 tests failed.  (1 test was not run).」（sha256
  4670d4c145274d761ab5383d7d9e570f19b8808a661aa9ee1bc70e0582fa42dd）

## 适用边界与反例

- 适用：抛点在**被交付的库头**、且该惯用法是库的主要错误出口。
- 反例：抛点只在上游测试代码里、库本体正常 ⇒ 用 `E543-draft-7707` 的
  `-std=gnu++98` 重编方案，**不要**打 `noexcept(false)` 补丁。
- 若同一份源码两处都有抛出析构：库头走本条、测试目标单独降档，两件事分开做、
  分别留证据，不要用一条 `-std` 旗标同时解决。
- 若该头同时作为 C 头文件导出：`noexcept` 是 C++ 关键字，须确认只在 C++ 编译单元里
  展开（本包该头为纯 C++ 头，无此问题）。
- `noexcept(false)` 只恢复可传播性；消费者若不从异常路径退出（如 C 侧调用栈），
  仍需另加错误码出口，本条不覆盖。

## 关联条目

- **对照（非命中）**：`knowledge/drafts/E543-draft-7707.md` 与同名 `.kv`——
  同一条 C++11 析构隐式 `noexcept` 机制，不同 locus；本条是对其
  `forbid_1`（`.md:73-74`、`.kv:34-36`）适用面的收窄。
- ⚠ **E 号在池内被大量复用**：`knowledge/drafts/` 下以 `E543-draft-` 开头的条目实测
  52 份 `.kv`（含同名 `.md` 共 104 件），其中 `DRAFT-E543-ohos-conan-run-shell-quote-cstring`
  是完全不同的机制（conan run 的 shell 引号/cstring）。**引用一律按文件名**
  `E543-draft-7707`，不要只写「E543」。
- 同名单行但**不同机制**（勿混用）：`E293.kv:41-43`、`boolstuff/0.1.16`
  补丁 0002、`aldo/0.7.8/conanfile.py:363-387`、
  `DRAFT-cxx17-removed-constructs-compile-out-via-feature-macro`
  都写作 `throw(T)` → `noexcept(false)`，但那是 **C++17 删除动态异常规范**的
  **编译期**修复（普通成员函数上的 `throw(Error)`/`throw(AudioException)`）；
  本条是**析构**的隐式 `noexcept` 导致的**运行期** `std::terminate`，
  签名、阶段、根因都不同。`glaze/8.3.0`、`libfex/0.1.0` 两处则是
  `std::expected` polyfill 里的 `noexcept(false)`，同属另一族。
- 同包不同面：`DRAFT-jellyfish1-1.1.11-gtest-tr1-tuple-header-flags`
  （vendored googletest 的 `<tr1/tuple>` 编译期缺口，配送池件，不占本 PR 知识位）。
- 实证案例：jellyfish1 1.1.11 真机适配（2026-09-25，B 机，
  clang 15.0.4 + libc++abi + cppstd=17，补丁 0001）。
