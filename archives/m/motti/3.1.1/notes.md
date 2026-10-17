# motti 3.1.1 适配笔记

## 任务信息

- 平台任务号：7364（活动：开源鸿蒙PC专项积分赛-依赖）
- 分支：feat/motti-3.1.1；worktree：~/qzy/GLM-20-motti-3.1.1
- 上游：GNU motti 3.1.1（https://ftp.gnu.org/gnu/motti/motti-3.1.1.tar.gz，
  sha256 632d9a84…de429）
- 语言：C++（lang-preflight：task=cpp detected=cpp，通过）；构建系统：autotools（configure 现成，AC_PROG_CXX + AC_PROG_LIBTOOL，2014 年 autoconf 2.59 世代）
- 主理 agent：GLM-20

## W0 依赖检查

- 零外部依赖。SCT 备注标"ncurses 战棋"系误标：源码实际用 termios 处理终端
  （include <termios.h>），无任何 curses/ncurses 引用（grep 证据）。
- preflight 无依赖声明；无需 conan download 验证。

## W0b 历史经验

- 仓库无 motti 历史归档，首次适配。

## 上游测试清点（R51 证据）

otti/Makefile.am：`bin_PROGRAMS = motti testmotti`、`TESTS = testmotti`。
testmotti.cpp 的 launchTest()：JSON 解析演示 + LoginService/SessionService/
GamePersistanceService 服务演练（cout 打印）；六个 *Test 类（BoardTest/
GameManagerTest/MapManagerTest/SerializerTest/StringDrawerTest/
MottiRulesManagerTest）的 testAll() 调用**全部被上游注释**，main 恒 return 0。

| 维度 | 数量 | 说明 |
|---|---|---|
| 上游静态声明 N_static | 1 | TESTS=testmotti 注册 1 个测试程序（make check） |
| 构建注册 N_registered | 1 | automake check_TESTS = testmotti |
| 实际执行 N_executed | 1 | make check 实跑 testmotti，退出码 0（程序内无断言，"通过"仅指退出码） |
| 消费者测试 N_consumer | 1 | test_package/test.cpp，8 项断言（N_assertion=8） |

## 适配要点

- 产物：libmottifram.a（框架库）+ 头文件（include/motti/）+ motti、testmotti
  可执行（上游覆盖 bindir=$(exec_prefix)/bin/games）。
- package_type=library（混合包：可消费的框架库 + 工具可执行）。本 OHOS 适配版
  conan（2.29.1 CPS 改造）对 application 包不传播 includedirs/libs（aamath/
  aa3d 等 application 归档先例均显式置空），消费者测试拿不到框架头文件，故按
  library 声明传播；bindirs 非空 + commands.json（type=tool）满足 PF8 混合包判定。
- 因 library 型要求声明 shared 选项（conan 强制），上游仅静态库，validate 拒绝
  shared=True。
- 软件级 commands.json 按 R38 声明（motti 支持 --version/--help，otti.cpp
  verifyVersionHelp）。

## 构建补丁（patches/，均 refresh-patch --auto 生成）

1. `0001-config.sub.patch`：2014 年上游 config.sub 不认识 aarch64-*-linux-ohos
   三元组（"Invalid configuration"），在 maybe_os case 与 OS 校验列表两处加
   `linux-ohos*`/`-linux-ohos*`。验证：`/bin/sh ./config.sub
   aarch64-unknown-linux-ohos` 回显原串 rc=0。conandata strip: 1。
2. `0002-configure.patch`：config.status 临时目录 `umask 077`→`umask 022`
   （E011：HMDFS UID 映射导致 0700 目录不可写，`can't create
   ./confXXXX/subs1.awk: Permission denied`）。conandata strip: 1。

## E386 CONFIG_SHELL 处置

profile [buildenv] 注入 `CONFIG_SHELL=/data/service/hnp/bin/bash`（HNP bash，
HMDFS 上 getcwd 失效），autoconf 报 `working directory cannot be determined`。
按经验汇总 §1053 口径：放弃 autotools.configure()，build() 内
`self.run('cd <src> && CONFIG_SHELL=/bin/sh SHELL=/bin/sh /bin/sh configure
--prefix=... --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos')`
+ 源码目录内原地 make（无深层 build-release 子目录，避免 getcwd 风暴）。
AutotoolsToolchain 保留在 generate() 提供 CC/CXX env（删除它会导致 configure
`C++ compiler cannot create executables`，ac_cv_env_CC 为空）。

## 消费者测试设计记录

8 项断言：Board(10,10)/Board(4,7) 尺寸、Case(bool,Player*,CASETYPE) 属性回读、
setCase/getCaseNoThrow 读回、越界 getCaseNoThrow(99,99)==nullptr、
generateJson() 含 xsize/ysize 字段、setCaseType(LOCKED) 往返、
Case::generateJson() 非空。
**未纳入**：Board(std::string) JSON 往返构造——上游 2014 年 JSON 解析实现对该
输入段错误（LastTest.log 证据，conan-verify 第 8 轮实测）；属上游代码缺陷而非
适配问题，消费者测试不依赖该构造路径。

## 路径 B 判断

构建坑（E386/umask/config.sub 三元组）均为知识库已知条目（E011/E386/§12.24a），
本轮按既有知识修复并验证，无跨仓库复用的新知识增量 → **纯路径 A**。
---

**编译结束**: 2026-09-13 14:09
**最终状态**: built
