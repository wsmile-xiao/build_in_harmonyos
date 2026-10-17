# cute_aseprite 1.0.0 适配笔记（Bootstrap 阶段）

## 状态
- 阶段: bootstrap（R01，未进入 adapt/编译/W3/finish/submit）
- 任务: cute_aseprite-1.0.0-r01-bootstrap-and-adapt-pc1-64-20260829T154005Z
- 执行端 worktree: /storage/Users/currentUser/junshi_liu/worktrees/pc1-64-cute-aseprite-1.0.0
- 分支: feat/cute_aseprite-1.0.0（HEAD 2d5de502d8a5ac43f2cf9c6a4c71dd737d0fd644，origin/main 基线）

## 来源核验（2026-08-29）
- 官方仓库: https://github.com/RandyGaul/cute_headers（master 分支确认存在，
  `git ls-remote --tags` 无任何 tag，GitHub releases API 为空）
- cute_aseprite 为该仓库内单头文件 cute_aseprite.h；独立仓库 RandyGaul/cute_aseprite 不存在（404）
- 版本锚定: 上游无 tag/release，头文件内部版本宏与修订历史为准
  - "1.00 (08/25/2020) initial release" 于提交 6400bca5 引入，与任务版本 1.0.0 对应
- 源码校验值:
  - cute_aseprite.h @ 6400bca5: sha256 de5e855ac1de7f08a43dc5ae57afec6c64716933ccba4a168506c4500573214d
  - 交叉验证: codeload tarball 解包文件 与 raw URL 下载文件 sha256 一致
- 上游无独立 LICENSE 文件（LICENSE 于 2026-06 才添加，为 Zlib/Unlicense 双许可；
  1.0.0 时刻头文件未内嵌许可文本，v1.04 master 头文件尾部含 Zlib/Unlicense 双许可文本）

## 归档骨架（已建立）
- archives/c/cute_aseprite/manifest.yaml（软件级）
- archives/c/cute_aseprite/README.md
- archives/c/cute_aseprite/1.0.0/manifest.yaml（版本级）
- archives/c/cute_aseprite/1.0.0/conandata.yml（官方 raw URL + sha256）
- archives/c/cute_aseprite/1.0.0/conanfile.py（header-library 最小配方骨架）

## 待办（Adapt 阶段）
- conan create 本地验证（G1-G4/L2-L5）
- test_package/ 最小用例（加载并解析一个 .ase 样例）
- W3/finish/submit（由后续轮次按 SKILL.md 流程执行）
---

**编译结束**: 2026-08-30 08:49
**最终状态**: built
