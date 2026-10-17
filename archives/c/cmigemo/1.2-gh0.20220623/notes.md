# cmigemo 1.2-gh0.20220623 适配笔记

## 软件信息
- 软件：cmigemo 1.2-gh0.20220623（上游 koron/cmigemo main 分支 2022-06-23 快照，commit e0f6145f61e0b7058c3006f344e58571d9fdd83a；1.2 系代码线，HEAD 含 #29 merge fix-parallel-install）
- 任务号：6530（活动：开源鸿蒙PC专项积分赛）；分支 feat/cmigemo-1.2-gh0.20220623；worktree ~/qzy/cmigemo
- 构建系统：自定义 configure + Make（compile/Make_gcc.mak）
- 编译日期：2026-09-08
- 编译器：clang 15.0.4（OHOS SDK LLVM）
- 状态：published（conan-verify G0-G4/L2/L4/L5 全 PASS）
- 源码：https://github.com/koron/cmigemo/archive/e0f6145f61e0b7058c3006f344e58571d9fdd83a.tar.gz
  SHA256 beef9e7d362713f54879f22191408ee5c80ec4b9bf6bbc215f7d4316a545bc85

## W0/W0b
- W0：库与工具构建零强制外部依赖（纯 C + libc）。dict 目标需 nkf + perl + 联网下载
  SKK-JISYO.L（https://skk-dev.github.io/dict/SKK-JISYO.L.gz），属运行字典数据构建，
  不在配方内执行；配方 tool_requires nkf/2.1.5（制品仓已发布，满足上游 Makefile 的
  工具存在性）。
- W0b：本仓库无 cmigemo 历史归档；CI 能力矩阵 make/clang ✅。
- lang-preflight：PASS（task=cpp, detected=cpp）。

## 版本口径
- 上游 tags 中 rel-1_2 为 2003-12-29 的旧 tag；GitHub 无 "gh0.20220623" tag/release。
  任务版本对应的真实源码为 main 分支 2022-06-23 当日最后提交
  e0f6145f61e0b7058c3006f344e58571d9fdd83a（GitHub API commits?until=2022-06-24 实证，
  README 版本线为 1.2 系），conandata.yml 直接指向该 commit 的归档 URL。

## 配方要点
- basic_layout + `get(strip_root=True)`；build() 内生成等价 `config.mk`
  （上游 configure 仅展开该模板并硬性要求 nkf/qkc，库/工具构建不依赖字典），
  沿用上游默认相对路径（srcdir=./src/、objdir=./build/object/、outdir=./build/）。
- `make -f compile/Make_gcc.mak CC=<profile clang> CFLAGS_MIGEMO='-fPIC -O2'
  LDFLAGS_MIGEMO=` 命令行变量覆盖（命令行优先级高于 makefile 内定义），清空上游
  写死的 `-rpath /usr/local/lib`（R33/PF6）。
- 产物路径注意：Make_gcc.mak 的库目标无 outdir 前缀——`libmigemo.so.1.1.0` 及其
  soname 软链落在源码根；`cmigemo` 工具落在 `build/`。package() 分别拷贝。
- 上游只提供动态库目标（libmigemo.so.1.1.0，soname libmigemo.so.1），无静态库目标，
  package_type=shared-library。
- test_package 以 VirtualRunEnv（env="conanrun"）注入 LD_LIBRARY_PATH 运行消费者。

## 上游测试统计与执行（R51）
- 静态清点：上游无自动化测试套件——顶层 Makefile 无 check 目标；无 CTest/pytest 等
  注册入口；src/testdir/ 仅含 profile_speed.c 与 romaji_main.c 两个手动基准工具
  （main 函数交互式输入，无断言）。上游自动化测试静态总数记 **0**（清点证据：
  Makefile、compile/Make_gcc.mak、src/testdir/ 目录清单）。
- 消费者测试（test_package）补位验证库可用性：随包携带最小 UTF-8 字典
  （migemo-dict，tokyo/osaka 两词条），消费者程序 migemo_open 打开字典 →
  migemo_query("tokyo") 生成查询正则 → 断言包含候选词「とうきょう」→
  migemo_release/migemo_close。
- conan create 测试阶段实跑输出：
  `query regex: (トウキョウ|とうきょう|tokyo)` + `cmigemo consumer test passed`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 "Require qkc or nkf" | 上游 configure 硬性要求编码工具（仅字典构建用） | 配方生成等价 config.mk，跳过 configure；tool_requires nkf/2.1.5 |
| 2 | make 报 No rule to make target main.c | config.mk 用绝对路径与 conan 拷贝后的目录不一致 | 沿用上游相对路径 + make cwd=源码根 |
| 3 | 消费者运行报 libmigemo.so.1 not found | 动态库运行时搜索路径 | test_package 加 VirtualRunEnv，env="conanrun" 运行 |
| 4 | 包内缺 libmigemo | Make_gcc.mak 库目标无 outdir 前缀，产物在源码根 | package() 从源码根拷贝 libmigemo.so* |

## 依赖版本
- 无运行时依赖；构建工具 nkf/2.1.5（未实际使用——未构建字典目标）

## 验证结果
- conan-verify：G0 PASS / G1 PASS / G2 PASS（conan create 干净构建 + 消费者实跑）/
  G3 PASS / G4 PASS / L2 PASS / L4 PASS / L5 PASS
- 上游套件：0（无自动化测试）；消费者测试 1/1 通过

## 注意事项
- 字典（dict/ 目标）需联网下载 SKK-JISYO.L 且需 perl/nkf，配方不构建；运行时
  migemo_open 需要外部提供 migemo-dict 文件，消费者测试已用最小字典验证 API 链路。
- dict.mak 默认生成 CP932 编码字典；test_package 证明 UTF-8 字典可被 cmigemo
  正确读取（charset.c 自动检测）。
---

**编译结束**: 2026-09-08 23:49
**最终状态**: built
