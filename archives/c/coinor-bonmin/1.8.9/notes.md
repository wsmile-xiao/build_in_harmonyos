# coinor-bonmin 1.8.9 — OpenHarmony 适配笔记

## 基本信息
- 软件: coinor-bonmin（COIN-OR Bonmin，混合整数非线性规划 MINLP 求解器）
- 版本: 1.8.9（上游 tag `releases/1.8.9` = `030d111af16a0f30b6fff851ba7f983bea14f982`）
- 构建系统: autotools（**在 `Bonmin/` 子项目上 configure**；GitHub 归档不含 all-in-one 的
  CoinUtils/Osi/Clp/Cgl/Cbc/Ipbot 目录，根 configure 只会得到空 subdirs，不用它）
- 目标三元组: `aarch64-unknown-linux-musl`（由新件 config.guess 的 HarmonyOS 分支给出）
- 构建日期: 2026-09-24
- 产物: `lib/libbonmin.a`（静态）+ `include/coin/*.hpp`（60 个，含 `BonminConfig.h`）
  + `lib/pkgconfig/bonmin.pc` + `share/coin/doc/*`；**无 `bin/`**（见 ASL 段）
- 依赖: cbc/2.10.13、coinor-ipopt/3.14.19、clp/1.17.10、coin-or/0.108.12（=Osi）、
  coinutils/2.11.13、cgl/0.60.10.1、zlib/1.3.1（间接 mumps/5.9.1、openblas/0.3.28）

## 依赖链实证（W0）
- `conan list -r=ohpcd` 逐个实证在档：osi 面有 `coin-or/0.108.12`（**权威名是 coin-or**，
  `coin-utils`/`ipopt`/`coinor-cbc` 无此 ref）、`coinutils/2.11.12·2.11.13·2.11.13.1`、
  `clp/1.17.10·1.17.11`、`cgl/0.60.10·0.60.10.1`、`cbc/2.10.13`、`coinor-ipopt/3.14.19`、
  `metis/5.1.0`、`mumps/5.9.1`、`openblas/0.3.28+`、`zlib`。`metis` 在档但 **Bonmin 自身
  configure 不探测 Metis**（Metis 属 all-in-one 的 ThirdParty 面），故本包不 requires 它。
- 动态 `conan install`（`-pr:h/-pr:b` 双**绝对路径** profile `$TARGET_REPO/ci/conan/profiles/ohos-aarch64`，
  `--build=never`）rc=0，9 包全解析（cbc 二进制 252.8MB 自 ohpcd 下载）。
- 编译期 link 顺序实测：建 `osi-clp.pc` 别名后 `pkg-config --exists "cbc osi-clp ipopt"`=YES，
  实链覆盖 CoinIO-gz 路径的探针 rc=0（gzopen/gzread 真入二进制）；**反例**去掉 `-lz`
  → rc=1、4 个 undefined `gz*`（证明顺序面是真依赖，不是空过）。
- `git show upstream/main:…` 官方配方参照（平台存量配方=最高参照）：
  `archives/c/cbc/2.10.13/conanfile.py`（--with-*-lib 绝对 .a 注入 + sed 换 -l*、
  osi.pc/osi-clp.pc 兼容别名、config.guess sed 注入、HMDFS config.status conftmp 修复）、
  `archives/c/coinor-ipopt/3.14.19/`（config.guess/config.sub/configure 三补丁、coinmumps.pc 混链、
  LD_LIBRARY_PATH prepend、.la 移除）、`archives/c/clp/1.17.11/`（config.guess 注 HarmonyOS→musl）。

## 缺依赖与 ASL 处置（任务卡要点）
- **ASL 不在档**（`conan list -r=ohpcd`：`asl`/`coinor-asl`/`ampl-asl` 均 0 条）。
- 实际机制（比开关更硬）：`Bonmin/configure.ac` 的
  `AC_COIN_CHECK_PACKAGE(ASL, [ipoptamplinterface], [BonminAmplInterfaceLib])` 探测失败 ⇒
  `coin_has_asl=no` ⇒ 三处 `if COIN_HAS_ASL` 结构闸关闭：
  ①`src/CbcBonmin/Makefile.am` 不建 `libbonminampl.la`；
  ②`test/Makefile.am` 不建 AMPL 段（`InterfaceTest.cpp:284-386` 的
  `#ifdef COIN_HAS_ASL` 块整体编译掉，`test/mytoy.nl` 因此**从不被读取** ⇒ 计 **SKIP**）；
  ③`src/Apps/Makefile.am` 的 `bin_PROGRAMS = bonmin` 关闭 ⇒ **本包无 CLI** ⇒
  R38 判「库型」，软件级 `commands.json` 不适用（链上「有 CLI 则做」分支）。
- **任务卡的 `--disable-sAMPL-interface` 在 1.8.9 的 configure 选项表里不存在**
  （`./configure --help` 与全文 grep 均 0 命中）：传它只会留 `unrecognized options`
  warning、无任何作用，故**不传**；意图（关 AMPL 面 + .nl 计 SKIP）已由上述结构闸
  更硬地达成（编排方 2026-09-24 裁决：按此处置并留痕）。
- 可选依赖同样缺省跳过：FilterSQP（`coinfiltersqp` 0 条）、CPLEX（`osi-cplex` 0 条）。

## 关键适配点（按发现顺序）
1. **2007 版 config.guess/config.sub 整文件换新件**（先例集 #1）：旧件不认 `aarch64`
   也不认 `linux-musl`，光注 HarmonyOS 分支没用；新件取自权威源
   `https://git.savannah.gnu.org/cgit/config.git/plain/{config.guess,config.sub}`
   （timestamp 2026-05-17），并注入 `*:HarmonyOS:*:*|*:HongMeng:*:*) → aarch64-unknown-linux-musl`。
   实测 `./config.guess` → `aarch64-unknown-linux-musl` rc=0；`./config.sub` 同值 rc=0。
2. **CC/CXX 必须裸名 `clang`/`clang++`**：绝对路径 `/data/service/hnp/bin/clang` 命中
   coin m4 的 `case "$CC" in clang*) ;; cl* | */cl* …`（路径含 `/cl`）⇒ `coin_cc_is_cl=true`
   ⇒ `--enable-pkg-config` 默认被关、pkg-config 全程不跑 ⇒ configure 硬错
   `Required package Cbc or Ipopt not available`（首测 rc=1 复现）。同时显式传
   `--enable-pkg-config`。设备与 worker PATH 均含 `/data/service/hnp/bin`（init-build env 检查实证）。
3. **HMDFS `mktemp` 假绿（补丁 0003）**：`config.status` 建 `./confstatXXXXXX` 用
   `umask 077 && mktemp -d`（0700）⇒ 落盘 `drwx--S---` 且目录内写文件 `Permission denied`
   ⇒ 日志里 `config.status: creating Makefile` 之后紧跟 `mv … Permission denied`，
   **rc=0 却一个文件都没生成**（首测：Makefile/config.h/bonmin.pc 全缺、85 处 Permission denied）。
   修法 = `mkdir -p conftmp` + `umask 022`（E678/cbc conftmp 同款）。配方在 configure 后
   **断言 5 个关键产物落地**（Makefile/config.h/config_bonmin.h/bonmin.pc/libtool）才进 make。
4. **依赖 `.la` 与「归档合并」双坑（本包与 cbc 方案 B 的关键分歧）**：
   - 直接用 pkg-config 的 `-l*` ⇒ libtool 解析 `//lib/libCbc.la` 报
     `is not a valid libtool archive`（首测 make rc=2）。
   - 照 cbc 方案 B 把 `-l*` 换成**绝对 .a 路径** ⇒ 修好了 `.la`，但 libtool 把这些归档
     **合并进本包静态库**：`libbonmin.a` 膨胀到 **1,718,842,488 B（1.7GB）**、成员里内嵌
     18 个依赖 `.a`（且重复）。cbc 包 250MB 即同机制产物。
   - **正解**：把 5 个带 `.la` 的依赖包（cbc/clp/coin-or/coinutils/cgl）的 `-L` 重定向到
     build 内 `dep-libs/`（只放 `.a` 符号链接、无 `.la`）：`.la` 找不到、`-l` 语义保留、
     不触发合并。实测 `libbonmin.a`=**2,840,996 B（2.8MB）**、成员 62、嵌套 `.a`=0。
5. **CFLAGS 双钉**（coinor 铁律）：configure 期与 make 调用行都传
   `CFLAGS/CXXFLAGS='-O3 -pipe -DNDEBUG'（`-DBONMIN_BUILD` 在独立 `CDEFS` 变量，不受覆盖影响）。
6. **shared 判决**：用静态闭包实链 `-shared` 报
   `R_AARCH64_ADR_PREL_PG_HI21 … z_errmsg … recompile with -fPIC`（zlib 静态件非 PIC）
   ⇒ 本包默认 **static**（cbc 同族形态），不硬做 shared。

## 测试结果（设备实测）

### 上游标准 test 套件（入口 `Bonmin/` 下 `make test`，已进配方 build()）
| # | 用例 | 注册依据 | 结果 | 说明 |
|---|------|----------|------|------|
| 1 | `unitTest`（`test/InterfaceTest.cpp`） | `test/Makefile.am` `noinst_PROGRAMS`（ASL 条件段之外仍注册） | **PASS** | 输出 `Test OsiTMINLPInterface with Ipopt solver` / `All test passed successfully` |
| 2 | `CppExample`（`test/MyBonmin.cpp`+`MyTMINLP`） | `test/Makefile.am` `noinst_PROGRAMS` + `test:` 目标 | **PASS** | `Cbc0001I Search completed - best objective -2.500141411335916`，1 node |
| 3 | `test/mytoy.nl`（`.nl` 数据用例） | `test/*.nl` 文件（`test:` 经 unitTest 消费） | **SKIP** | `InterfaceTest.cpp:284-386` 整段 `#ifdef COIN_HAS_ASL`；ASL 不在档 ⇒ 文件从不被读取 |

- 清点口径：**框架注册数**（`test/Makefile.am` 的 `noinst_PROGRAMS`+`test:` 目标）= 2，
  **`.nl` 数据用例数**（`test/*.nl`）= 1，**N（候选数法取最大值并单列 .nl）= 3**；
  N′=2 实跑、PASS=2、FAIL=0、SKIP=1、NOT_RUN=0。四种口径不混用。
- 运行期前置：`LD_LIBRARY_PATH` 必须含 coinor-ipopt/openblas 的 lib 目录（`libipopt.so`），
  否则 `Error relocating ./unitTest: Ipopt::… symbol not found`（exit 127）——
  配方 build() 显式注入，test_package 由 `env="conanrun"` 提供。

### 消费者 / HarmonyOS 专项（test_package，2/2 PASS）
| 用例 | 断言数 | 结果 |
|------|--------|------|
| `bonmin_smoke` | 3（可行解 / `mipStatus==FeasibleOptimal` / `bestObj==-2.500141411335916`±1e-6） | PASS |
| `bonmin_ohos_test` | 3（安装头 `BONMIN_VERSION=="1.8.9"` / `IpoptApplication::Initialize()==Solve_Succeeded` / 完整 B-BB 最优值+`numNodes>=0`） | PASS |

## CLI（R38）
本包**不产出任何可执行文件**（`bin_PROGRAMS=bonmin` 被 `if COIN_HAS_ASL` 关闭，安装树
`bin/` 为空、`INST_BIN=0` 实测）⇒ 库型包，**不创建 commands.json**。

## 注意事项
- 消费者链接走 `cpp_info.requires` 传递完整静态闭包（cbc/clp/coin-or/coinutils/cgl/zlib +
  coinor-ipopt）；`package()` 会删除 libtool 生成的 `.la`（依赖绝对路径烤死，同 coinor-ipopt）。
- `test_package/MyTMINLP.{hpp,cpp}` 取自上游 `examples/CppExample`（EPL-2.0，文件头保留原版权），
  提供被测 MINLP 的问题定义供两个消费者程序复用。
- 上游 `make test` 依赖 test/ 子目录（`Bonmin/Makefile.am` 里 `if ALWAYS_FALSE` 才进 SUBDIRS），
  必须显式 `make test` 才会构建并运行，`make`/`make check` 不覆盖它。

---

**编译结束**: 2026-09-24
**最终状态**: built
