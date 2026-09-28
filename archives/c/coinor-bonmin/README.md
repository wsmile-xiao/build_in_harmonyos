# coinor-bonmin

**COIN-OR Bonmin** — 开源混合整数非线性规划（MINLP）求解器，实现 B-BB（以 Ipopt 解
NLP 子问题、Cbc 做分支定界）及其割平面/启发式族，是 COIN-OR 优化栈的上层求解器之一。

- 上游仓库：https://github.com/coin-or/Bonmin
- 许可证：EPL-2.0
- 构建系统：autotools（在 `Bonmin/` 子项目上 configure）
- 已收录版本：[1.8.9](1.8.9/)

## 依赖（均在 ohpcd 制品仓在档）

| conan ref | 角色 |
|---|---|
| `cbc/2.10.13` | MILP 分支定界内核（传递 coinutils/coin-or/clp/cgl/zlib） |
| `coinor-ipopt/3.14.19` | NLP 子问题求解器（传递 mumps/openblas） |
| `clp/1.17.10` | LP 内核，提供 `OsiClp`/`ClpSolver`（pkg-config 模块名由本包写别名 `osi-clp.pc`） |
| `coin-or/0.108.12` | Osi 求解器接口（注意权威名是 **coin-or**，不是 osi/coinor-osi） |
| `coinutils/2.11.13` / `cgl/0.60.10.1` / `zlib/1.3.1` | 基础工具/割平面/压缩 IO |

**不在档因而未启用**：ASL（AMPL `.nl` 接口，`--disable-sAMPL-interface` 开关在 1.8.9
configure 中不存在，实际由 `if COIN_HAS_ASL` 结构闸关闭）、FilterSQP、CPLEX。

## 产物形态

静态库 `libbonmin.a` + `include/coin/*.hpp` + `lib/pkgconfig/bonmin.pc`。
**无命令行工具**（`bin_PROGRAMS=bonmin` 属 ASL 条件段），因此本包不声明 `commands.json`。

## OHOS/HarmonyOS 适配要点

1. `config.guess`/`config.sub` 为 2007 旧件（不认 aarch64、不认 linux-musl）⇒ 整文件换
   新件并注入 `HarmonyOS|HongMeng → aarch64-unknown-linux-musl` 分支。
2. `config.status` 的 `mktemp -d`（0700）在 HMDFS 上自身写不进 ⇒ 改 `mkdir -p conftmp` +
   `umask 022`，否则 `configure` rc=0 却不产出 Makefile/config.h（假绿）。
3. `CC/CXX` 必须**裸名** `clang`/`clang++`：绝对路径会被 coin m4 的 `*/cl*` 分支判成 MSVC，
   连带把 pkg-config 探测整体关掉。
4. 依赖包 `.la` 内 `libdir='//lib'` 无效；但改成绝对 `.a` 路径会让 libtool 把依赖归档
   **合并进本包静态库**（实测 1.7GB）⇒ 正解是本地「只放 .a、无 .la」的符号链接目录
   并把 `-L` 重定向过去（实测 2.8MB）。
5. `CFLAGS/CXXFLAGS='-O3 -pipe -DNDEBUG'` 在 configure 期与 make 调用行**双钉**。
