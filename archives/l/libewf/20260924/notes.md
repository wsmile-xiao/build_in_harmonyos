# libewf 20260924 适配笔记

## 编译环境

- 构建系统: autotools（release 资产自带预生成 configure/Makefile.in，无需 autoreconf）
- 编译日期: 2026-10-10
- 编译器: clang 15（OHOS 工具链，Target: aarch64-unknown-linux-ohos）
- 状态: built（本机 conan create RC=0，test_package 全绿）

## 源码溯源（2026-10-09 实测）

1. 上游 GitHub（libyal/libewf）release tag 20260924 存在；release 资产
   libewf-experimental-20260924.tar.gz → HTTP 200（本配方采用，2681717 字节，
   sha256 e2da4fdb…905b5）。
2. 任务卡给定 codeload git tarball 不含 configure/Makefile.in/config.guess
   预生成产物，也不含 22 个 libyal 支持子库（tar 内实测全 MISSING）；
   synclibs.sh 需构建期逐库 git clone，违反本仓"never pulls unregistered
   dependencies"规范；且 CI worker PATH 无 automake，bootstrap 不可行。
3. release experimental 资产为上游发布流水线 synclibs+autogen 后的自包含
   快照（configure + 22 子库内嵌），同族先例 libvmdk/20260714（PR #15170）
   同通道同规范。

## 平台适配（全部内联 build()，零 patch）

1. E011（HMDFS umask）：configure 内 2 处 umask 077 → 022，全程 umask 022。
2. 三元组：config.guess（2025-07-10）无法识别 HarmonyOS，显式
   --build/--host=aarch64-unknown-linux-gnu。
3. CONFIG_SHELL 显式启动 configure（HMDFS 脚本执行）。
4. 上游 autotest 测试：autom4te 取 OHOS hnp 工具链（autoconf 2.72），
   PATH 前置后 make check 完整真跑；LD_LIBRARY_PATH 注入构建树 .libs。
5. --disable-python / --with-libfuse=no。

## 测试统计

- 上游 autotest（OHOS 双 portability patch 修复后实测全过）：test_library 61/61、test_tools 17/17，合计 78/78。修复：①tmpfile(3) OHOS musl 硬编码只读 /tmp（TMPDIR mkstemp 替身）；②时区串 musl 格式 +01:00 (CET)（三段精确验证 67+37+29=133）。
- 消费者测试：test_libewf.c 35 + test_ohos.c 30 = 65 检查点，test_package 全绿。

任务卡 #15015，taskBranch=feat/libewf-20260924。
