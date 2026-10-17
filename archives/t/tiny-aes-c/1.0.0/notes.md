# tiny-aes-c 1.0.0 适配笔记

## 上游信息

- 上游仓库: https://github.com/kokke/tiny-AES-c
- 版本: v1.0.0 (tag commit e72b6eff0884673997d0ca6385169bbd9b31936d, 2019-02-01)
- 许可: The Unlicense（公有领域）
- 构建系统: CMake（`add_library(tiny-aes aes.c)`）+ 自带 Makefile（test.elf / aes.a）
- 语言: C（aes.c/aes.h），附带 aes.hpp C++ 头

## 适配要点

1. 上游 CMakeLists.txt 不安装头文件，配方 `package()` 显式拷贝 `aes.h`/`aes.hpp`
   到 include、`unlicense.txt` 到 licenses。
2. 模式宏在 aes.h 中带 `#ifndef` 守卫，默认 AES128 + CBC/ECB/CTR 全开；上游
   CMakeLists.txt 不传任何宏，默认构建即为 AES128 + 三模式，无需额外选项。
3. 官方 v1.0.0 tarball 由 `git archive` 生成（与 GitHub codeload 字节一致），
   SHA-256 = e47b84db2ea51d39ab967143c93b37df21431caaad7b6a793a3c9ef4dee3f221。
4. GitHub 主站直连超时（raw/codeload/git 通道可用），init-build 下载失败时改用
   `git clone + git archive` 离线备源（R39 官方源不变）。

## 上游测试 (R51)

- 上游测试: test.c（NIST SP 800-38A AES128/192/256 ECB/CBC/CTR 加解密向量，
  通过 `make test` 以 37 组断言运行）。
- 实测运行: `./test.elf` 输出 ECB/CBC/CTR encrypt/decrypt 全部 SUCCESS，0 失败
  （默认 AES128 配置；AES192/AES256 由 Makefile 目标切换编译宏，同一套向量）。
- 消费测试: test_package/test.c 复刻 AES128 ECB/CBC/CTR 三组 NIST 向量断言。

## 知识判定（executor_local_required，本地只读快照）

- 快照: /storage/Users/currentUser/tianyi/ohpc-knowledge-snapshots/tiny-aes-c-1.0.0-r01-bootstrap-and-adapt-pc2-6-20260908T130440Z
  （repository=gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git, ref=main,
  head=7285d042840352f4caa18ccf5f3a3ebc443e60c8, sparse=knowledge, 只读 a-w）
- 候选: CMake 4.1.2 拒绝 cmake_minimum_required(VERSION 2.8.12)
- 查重扫描: knowledge/graph（正式 E*.kv + doc/E*.md）、knowledge/drafts（*.md/*.kv）
- 命中: **E103**（等价命中）
  - error_signature（E103）: `CMake Error.*Compatibility with CMake.*3\.5 has been removed`
  - 实际报错: `CMake Error at CMakeLists.txt:1 (cmake_minimum_required): Compatibility with CMake < 3.5 has been removed from CMake` → 逐字匹配
  - root_cause 适用: CMake 4.x 移除 <3.5 兼容 → 与 tiny-aes-c 2.8.12 场景一致
  - rec_approach 适用: bump-cmake-minimum-version（sed 2.8.12→3.5）→ 已实施于 0001-CMakeLists.txt.patch
  - verification 适用: 补丁后 conan create G2 PASS
- knowledge_decision: **reuse_existing（路径 A）** — 不创建草稿，走路径 A 常规交付

## 基线隔离审计（同一 task_id 内）

- 现象: W3 本地 CI（JC5）报 `archives/u/util-linux-login/2.42.2/.ci-trigger` 未登记隐藏文件
- 归属审计: 该文件为其他库 util-linux-login 在本地 main（0b458be188）树中的空标记
  （blob e69de29b，内容空），origin/main（7285d042）树中不存在；不在本任务允许路径
  （archives/t/tiny-aes-c/1.0.0/**）内 → 判定为无关历史基线
- 处理: 临时 `git rm --cached` 隔离该精确路径 → W3 全门禁复验通过（L0/L1/L4/L5 pass）
  → 恢复 index（git add -f，blob 恢复 e69de29b）→ 随后按 W1 同步 origin/main
  （fast-forward 至 7285d042，该文件随上游删除自然消失，HEAD/index/磁盘均无残留）
- 恢复审计: git ls-files 无该路径、git status 无该路径变更；未 commit/push 任何基线改动
---

## r02 轮次（rule12 整改，2026-09-21）

- 背景: 外部 pc-pr-review 裁决 PR #9011 唯一失败项 rule12——PR 统计表"鸿蒙特有测试 N=0 < 1"
- 整改: test_package 新增鸿蒙特有测试 `test_harmony.c`（ctest 入口 `test_harmony`）：
  - E002 验证: `/tmp` 在鸿蒙 PC 上只读（EROFS），写入必须失败
  - 平台临时目录约定: `$TMPDIR`/`$HOME/tmp` 可写（HMDFS 真实文件 I/O）
  - 功能验证: AES-CBC 加密 → 密文落盘 → 重新读取 → 解密 round-trip，
    密文与 NIST SP 800-38A F.2.1 CBC-AES128 向量一致，解密逐字节还原明文
- 门禁复验: 上游测试台账 6/6 不回退；test_package 全量 2/2（test_tiny-aes-c + test_harmony）
  PASS；conan create G0–G4 复验通过；finish/W2/W3 复跑通过（W2 原子性 pass、W3 本地 CI
  模拟 pass、submit 就绪 pass）
- 知识判定: 复用 r01 快照（head 7285d042），无新候选，路径 A 维持，不创建草稿
- PR 统计表口径: 上游测试用例统计 6（不变）；适配后合计 7 = 上游实际运行 6 + 鸿蒙特有测试 1

**编译结束**: 2026-09-21 18:00
**最终状态**: built
