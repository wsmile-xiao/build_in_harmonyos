# qsort 0.1 适配笔记

## 编译环境
- 构建系统: header-only（单头文件 C 宏库，无 configure/CMake/Makefile 产物）
- 编译日期: 2026-09-18
- 编译器: clang/clang++ (15.0.4, OHOS 工具链 /data/service/hnp/bin)
- 状态: published

## 源码信息
- 上游: https://github.com/svpv/qsort（作者 Alexey Tourbin，MIT License）
- tag: v0.1 (git commit c65187313fc0df1fb81b842ca3094019dc56b8c3)
- tarball SHA-256: 0431b73341d8576c226c5a981ec301b2cb1112147da92a9baad9c5e6ed3613c9
- 文件: qsort.h（186 行，核心宏 QSORT）+ bench.cc（286 行，基准程序）+ Makefile + README.md

## 适配要点
- qsort.h 是 C 宏实现的快速排序（Sedgewick 1978），全部基于数组下标 + LESS/SWAP 宏抽象，
  调用方提供宏即可排序任意数据类型，甚至可同步排序多个关联数组。
- 纯 header-only 库：无编译产物、无链接目标。配方使用 header-library 类型，
  source() 下载官方 tarball 后仅需把 qsort.h 拷入 include/。
- bench.cc 为性能基准（与 libc qsort/std::sort/mjt 对比），非断言型测试，不入包。
- 无 CLI 产物 → 不需要 commands.json（R38）。
- 上游无测试框架/测试用例：Makefile 只有 all: bench 目标，无 check/test 目标。

## 验证结果
- test_package 消费者用例 test.c：QSORT 宏排序 10 个整数并断言升序，编译运行通过。
- conan create（OHOS aarch64）通过，包内 include/qsort.h 就位，test_package 编译链接运行通过。

## 知识候选与路径判断（知识库扩展任务）

- 台账: `knowledge-candidate-ledger.md`（四候选逐项七轴查重 + 覆盖/新增差异 + 关系字段 + 适用边界/反例）
- 候选 A（G1 要求 header-only build() no-op）: exact_duplicate=E257 → reuse_existing
- 候选 B（package() 中 `package_folder / "include"` 的 str/str TypeError）: 四范围查重未命中、
  已验证可跨库复用、combination/boundary novelty=true → **new_draft**（DRAFT-qsort-0.1-package-folder-str-path-join.kv/.md，同 stem 配对）
- 候选 C（E017 镜像注入残留需恢复官方 URL）: exact_duplicate=E415 → reuse_existing
- 候选 D（W3 JC 命中其他库基线状态文件）: SKILL 内嵌基线隔离流程，非知识候选
- 路径决定: **路径 B（知识库扩展）**，草稿与 qsort 归档同 PR 交付

## 注意事项
- QSORT 宏非稳定排序；使用者需自备 LESS/SWAP 宏（引用数组元素）。
- 头文件不依赖任何系统头文件以外的库，适配成本为零。
---

**编译结束**: 2026-09-18 01:09
**最终状态**: built
