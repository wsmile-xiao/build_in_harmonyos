# cccc 3.2.0 适配笔记

## 软件信息
- 软件：cccc 3.2.0（上游 sarnold/cccc，commit f3b6427 锚定，GPL-2.0-or-later 编译发行版）
- 定位：C/C++ 代码计数器（PCCTS 解析器驱动的结构化度量报告：HTML/XML/DB）
- 构建系统：递归 Makefile（顶层 Makefile 全部工具变量 `?=` 定义；all = mini + cccc + test）
- 任务号：#6232（活动：开源鸿蒙PC专项积分赛）；分支 feat/cccc-3.2.0；worktree ~/qzy/cccc

## W0/W0b
- W0 preflight：PASS（零依赖）
- W0b：本仓库无 cccc 历史归档；lang-preflight PASS（cpp 主体，make 构建系统，90 源文件 cpp:49/c:36）
- 版本锚定：仓库无 3.2.0 tag；CHANGELOG.md 首条 `## 3.2.0 (2022-11-13)` 与 master HEAD f3b6427 同日期，
  conandata 锚定该 commit 快照（cdbfasta #6245 git-snapshot 先例）

## 源码检查（commit f3b6427 快照，SHA256 e18d98bce3a0647161b348272dea6ecf908d00b24eccaa73c92b4317b32f56c2）
- Makefile 变量全部 `?=` 定义 → clang 经 make 命令行/环境直接覆盖，**无需任何源码补丁**（patches 为空）
- pccts（1990 年代 C 代码）在 clang 15 下仅告警编译通过；`all` 目标链式完成 pccts 工具 → 解析器生成 → 计数器构建 → 自测套件
- 已知限制：二进制横幅内嵌 "Version 3.1.6"（上游改了 CHANGELOG 未改版本串）；cccc 把未知 CLI 参数当输入文件名
  且退出码仍为 0（`-h` 报 "Couldn't open -h"）→ 消费者测试断言报告产物而非旗标解析

## 上游测试统计与执行（R51）
- 静态清点：`all` 目标包含 test 套件——20 个测试运行（prn1–prn16 单元输入 + test1–test4 回归输入），
  每个运行对生成的 db/html/xml 三类报告与仓库内置参考做 diff，合计 60 项输出比对
- 实际执行（设备，探索构建与配方 build() 内均执行）：60/60 diff 全部一致，套件输出 "All tests passed"，退出码 0
- 记录：~/tmp/uc2/cccc/build1.log

## 适配后测试（消费者，test_package）
- test.sh：以 C++ 样例文件驱动打包后的 cccc（--lang=c++ --outdir），断言：
  退出码 0、cccc.html/cccc.xml/cccc.db 三类报告生成、运行摘要含 "Primary HTML output"、HTML 含样例文件名（6 项断言）
- conan create（G2）内全部通过

## OHOS 平台要点
- 打包的 CLI 二进制按 E077 四步签名；签名器调用剔除 LD_LIBRARY_PATH（同 braa/svector）

## 验证记录
- conan-verify：G0-G4 + L2/L4/L5（reports/conan-verify-report.md，执行后回填）
- status：built（上传发布须等合并后 release 流水线）
---

**编译结束**: 2026-09-06 03:27
**最终状态**: built
