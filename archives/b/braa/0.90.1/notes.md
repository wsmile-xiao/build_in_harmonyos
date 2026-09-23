# braa 0.90.1 适配笔记

## 软件信息
- 软件：braa 0.90.1（上游 mteg/braa，GPL-2.0-only）
- 定位：大规模 SNMP 扫描器（SNMPv1/v2c get/set/walk，单进程并发查询，自实现 SNMP 栈）
- 构建系统：纯 Makefile（无 configure、无 install 目标、无 check 目标；链接行硬编码 `cc`；链接后 `strip`）
- 任务号：#6106（活动：开源鸿蒙PC专项积分赛）；分支 feat/braa-0.90.1；worktree ~/qzy/braa

## W0/W0b
- W0 preflight：PASS（conanfile 无依赖；上游自实现 SNMP 栈，仅依赖 libc）
- W0b：本仓库无 braa 历史归档/notes；lang-preflight PASS（task=cpp, detected=c，兼容族；
  证据：顶层 Makefile，5 个 .c 源文件占比 100%）
- recipe-search：语料 3679 条无相似配方；参照已合入同类纯 Makefile CLI 工具模式（aa3d 1.0）

## 源码检查（上游 v0.90.1 tarball，SHA256 677a20e21818540d749db9c9f6ce724e055da55f666481d454666efb43351594）
- 16 个文件：COPYING Makefile README VERSION braa.1 5×.c 4×.h mkrelease
- 风险点 1（命中）：Makefile 链接行 `cc` 硬编码（设备/CI 无 cc）→ 0001-Makefile.patch 改 `$(CC)`
- 风险点 2（命中）：链接后 `strip $(OUT)` → 补丁改 `-strip`（设备有 strip 可用；CI 交叉环境无/不兼容时仅降级）
- 风险点 3（排除）：8 处 `index()`（braa.c:128, queries.c 多处）未含 <strings.h> → 设备实测 OHOS musl
  提供该符号，链接与运行均正常，无需补丁
- 风险点 4（发现于 conan create）：queries.c 等使用 `assert(string = strdup(string))`（赋值在 assert 内）；
  Conan Release 环境 CPPFLAGS 注入 -DNDEBUG 会把 strdup 一并编译掉 → 首次查询解析即段错误（SIGSEGV，
  退出码 139，复现于打包产物）。上游默认 CFLAGS/LDFLAGS 为空、assert 生效，故配方显式 `CPPFLAGS=`
  保持与上游一致的构建语义
- 其他：Makefile 未定义 CPPFLAGS，会继承环境变量；CFLAGS/LDFLAGS 有定义，环境不注入

## 上游测试统计（静态清点）
- 上游无任何测试套件：静态 0、执行 0、跳过 0（tarball 无测试程序/测试框架，Makefile 无 check 目标）

## 适配后测试（消费者，test_package/test.sh，3 组 6 断言）
1. `braa -h`：退出 0，横幅 braa 0.90.1 + usage（grep 2 断言）— PASS
2. `braa -r 0`：退出非 0 + stderr "Invalid retry count."（2 断言）— PASS
3. `braa -v -a 5 -t 2 -r 1 127.0.0.1:.1.3.6.1.2.1.1.1.0`：真实 SNMP GET over UDP，
   断言 "1 queries made" + "0 queries acknowledged"（无本地 agent 超时属预期）（2 断言）— PASS
- conan create（G2）内 test_package 全部通过（2026-09-06，reports/conan-create.log）

## OHOS 平台要点
- 交叉构建产物需签名才能执行（E077）：工具链在产物内嵌未签名 .codesign 占位段，
  binary-sign-tool 直接签报 ".codesign section already exists"；配方 package() 内按
  E077 四步流程先 llvm-objcopy 移除该段再 selfSign 并 chmod
- binary-sign-tool 依赖系统 OHOS libc++（std::__h 符号）：Conan 环境的 LD_LIBRARY_PATH
  会让工具链 libc++ 遮蔽系统库导致重定位失败，调用签名器时剔除该变量
- 命令行工具 → 软件级 commands.json（type=tool）

## 验证记录
- conan-verify：G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS（2026-09-06，reports/conan-verify-report.md）
- G2 知识图谱命中 E540（shadow-ci/runner-path-prepend，仅环境提示，非本配方缺陷）
- status：built（上传发布须等合并后 release 流水线）
---

**编译结束**: 2026-09-06 00:55
**最终状态**: built
