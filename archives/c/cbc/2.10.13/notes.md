# cbc 2.10.13 — OpenHarmony 适配笔记

## 基本信息
- 软件: cbc (COIN-OR Branch-and-Cut MILP Solver)
- 版本: 2.10.13
- 构建系统: autotools（COIN-OR 递归 configure）
- 目标三元组: aarch64-unknown-linux-musl
- 构建日期: 2026-09-18
- 依赖: coinutils/2.11.13, coin-or/0.108.12 (Osi), clp/1.17.10, cgl/0.60.10.1, zlib/1.3.1

## R01 外部阻塞与 R02 解除（本版本核心）
R01（cbc-2.10.13-r01-pc1-19-20260915T173044Z，external_blocked/dependency_package_defect）：
- 首错：`CbcSolver.cpp:216:10: fatal error: 'CglLandP.hpp' file not found`（make 退出码 2，
  已链接 libCbc.a 71+ 对象后）
- 根因：已发布 cgl/0.60.10 包缺 CglLandP.hpp/CglLandPValidator.hpp 及 CglLandP 符号
  （configure 探测 osi-clp 失败致 COIN_HAS_OSICLP 未启用，CglLandP 源被条件宏跳过）
- 恢复：cgl/0.60.10.1 已发布（revision 9860081d，PR 10299 合入 main），
  包内 include/coin 含 CglLandP.hpp + CglLandPValidator.hpp（31 个头），
  libCgl.a 含 97 个 CglLandP 符号。R02 以 conan download 验证可消费后恢复构建，
  configure/make 全通过，CbcSolver.o 重新编译成功，cbc CLI 可运行。

## 关键适配点
1. **依赖注入**：cbc configure 用 AC_COIN_CHECK_PACKAGE 探测 coinutils/osi/clp/osi-clp/cgl，
   需 --with-coinutils-incdir/lib、--with-osi-incdir/lib、--with-clp-incdir/lib、
   --with-osiclp-incdir/lib、--with-cgl-incdir/lib 注入实际包路径（同 cgl/clp 先例）。
2. **pkg-config 兼容别名**：generate() 生成 osi.pc（Requires: coin-or）与
   osi-clp.pc（Requires: clp），否则探测失败。
3. **HMDFS**：umask 077 + SGID 使 configure 的 confstat 临时目录不可写，
   config.status 需 `mkdir -p ./conftmp` + umask 022 修复后重新生成 Makefile。
4. **config.guess**：sed 注入 `HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;`。
5. **上游测试数据**：make test 的 osiUnitTest/gamsTest 读取 `../../Data/Sample`，
   需从官方 coin-or Data-Sample 获取 MPS 放入 `<src>/Data/Sample`。
6. **OsiCommonTests 链接**：osiUnitTest 依赖 OsiCommonTest 符号，coin-or 包提供
   libOsiCommonTests.a 但 osi.pc 未声明，make test 需注入 `OSITESTS_LIBS=-lOsiCommonTests`。

## 测试结果（本机实测）
- gamsTest：exit 0，0 errors / 6 warnings（上游预期警告）
- osiUnitTest：1487 passed / 0 error / 10 warning（其中 2 expected）
- CInterfaceTest：exit 0 全部断言通过
- cbc CLI 冒烟（p0033.mps solve）：Optimal，obj=3089，exit 0
- 鸿蒙专项测试（0-1 背包，C 接口）：PASS，obj=14，解 (1,0,1)
- 消费者用例（生产混合 MILP，C 接口）：PASS，obj=130，解 (3,2)
- 双口径：source_declared_total=11（gamsTest 4 + CInterfaceTest 6 + OsiCbc 1），
  configured_executable_total=10（testProblemModification 被上游 main 注释排除），
  executed_passed_total=10，全量通过率 10/11=90.9%，当前配置可执行集合 10/10=100%

## CLI（R38）
构建产出 `cbc` 可执行文件（`Welcome to the CBC MILP Solver / Version: 2.10.13`），
软件级 archives/c/cbc/commands.json 已声明 type=tool、versions 含 2.10.13。

## 注意事项
- C 接口 `Cbc_setObjSense(-1)` 表示最大化（上游 CInterfaceTest 同款约定）。
- Cbc_loadProblem 使用压缩稀疏列格式；colub 缺省为无穷、collb 缺省 0。
- 库文件：libCbc.a / libCbcSolver.a / libOsiCbc.a；头文件安装于 include/coin。
---

**编译结束**: 2026-09-18 22:21
**最终状态**: built
