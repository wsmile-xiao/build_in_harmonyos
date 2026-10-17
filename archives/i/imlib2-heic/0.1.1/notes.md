# imlib2-heic 0.1.1 适配笔记（R01）

## 软件概述

imlib2-heic（github.com/vi/imlib2-heic，BSD-3-Clause）是 imlib2/feh 的
HEIC/HEIF 解码 loader 插件：编译产物为单个 `heic.so` 动态模块，由 imlib2 在
运行时 dlopen 到 `lib/imlib2/loaders/`。上游纯 makefile 构建（无 configure、
无 autotools），仅 1 个 C 源文件（loader_heic.c）。

## 构建系统与依赖

- 构建：`make` → `heic.so`（makefile + commands.mk；`-std=c99 -fPIC -shared`）
- 编译期强依赖：imlib2（`imlib2-config --libs`、`<Imlib2.h>`、imlib2 私有 ABI
  结构 ImlibImage/ImlibLoader）、libheif（`pkg-config libheif --cflags/--libs`）
- 依赖发布现状（ohpcd 制品仓，双次探测一致）：
  - libheif/1.22.2 ✅ 已发布（revision b9cc4f1bbf904a3702270a443dc85209）
  - libde265/1.0.18 ✅ 已发布
  - imlib2/1.12.6 ❌ **未发布**（`conan list 'imlib2/*' -r=ohpcd` 0 匹配；
    `conan download imlib2/1.12.6 -r=ohpcd --only-recipe` 报错；制品仓 API 无 imlib 包）

## 流程实录（R01，本 task_id 内）

1. worktree：从可审计 main（eabe58c074）创建唯一专用 worktree
   `/storage/Users/currentUser/zhuo/worktrees/imlib2-heic-0.1.1`，
   分支 `feat/imlib2-heic-0.1.1`（porcelain 仅 1 条匹配）。
2. 官方源码：tag v0.1.1 tarball（codeload），SHA-256
   `8e7771903ef2e8718e17f228e7fcdb1aeb889e57c9d846b6708d45b6310a3856`
   （两次独立下载核验一致；conandata.yml 已填）。
3. R47 lang-preflight：PASS（detected=c，c↔cpp 兼容族）。
4. init-build/conan-init：生成存档骨架；由模板改写为 makefile 配方
   （requires imlib2/1.12.6 + libheif/1.22.2，package 安装 heic.so 到
   lib/imlib2/loaders/）。
5. conan-verify G2（conan create，ohos-aarch64 profile）**真实首错**：
   ```
   ERROR: Package 'imlib2/1.12.6' not resolved:
   Unable to find 'imlib2/1.12.6' in remotes.
   Required by 'imlib2-heic/0.1.1@ohpcd/stable'
   ```
   知识图谱命中 E540 为误导（zlib shadow-ci 场景），实际根因即 imlib2 依赖缺失。
6. 上游测试台账：source_declared_total=0（上游无任何测试基础设施，8 文件全量枚举见
   reports/upstream-test-ledger.md）；构建被依赖门禁阻塞，0/0 硬门禁前置条件（构建成功）未满足。
7. 知识候选：3 项全部查重为既有覆盖/无验证新增（reports/knowledge-candidate-ledger.md），
   路径决定 `path_a_no_knowledge`，不建草稿。

## 阻塞归属与恢复条件

- 阻塞归属：真实外部依赖缺失（imlib2/1.12.6 未发布到 ohpcd 制品仓）；
  非当前库配方/构建错误，非平台限制。
- 恢复条件：分析端另行绑定 imlib2 适配任务并发布（配方已存在于未合入分支
  origin/feat/imlib2-1.12.6，含 conanfile/conandata/test_package/commands.json/
  审计报告）；发布后本任务以新 task_id follow-up 恢复 conan-verify 续跑其余门禁
  （构建→上游测试→HOS 专项测试→test_package→消费者验证→finish/W3→W4→PR/rebuild）。
- 本轮未 commit/push/创建 PR/触发 rebuild（高难度挑战门禁未满足，禁止交付）。

## 结果

status=dependency_missing（missing: imlib2），同 task_id 回报服务端。
---

**编译结束**: 2026-09-19 14:50
**最终状态**: built
