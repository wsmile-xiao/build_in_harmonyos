# perlinnoise 3.0.0 适配笔记

## 编译环境
- 构建系统: header-only（无编译步骤，纯头文件分发）
- 编译日期: 2026-09-05
- 编译器: clang/clang++（仅 test_package 编译消费者测试）
- 状态: built

## 编译步骤

perlinnoise 3.0.0 是纯 header-only 库（单个 `PerlinNoise.hpp`，C++17，MIT 协议，
`Reputeless/PerlinNoise` 官方 tag `v3.0.0`，commit `39ca7406`）。无 configure/make 步骤：

1. `conan create` 直接从官方 tarball（sha256 `1fea1e7e...e827fc`）解压；
2. `package()` 将仓库根目录的 `PerlinNoise.hpp` 复制到 `include/`（上游无 include/ 子目录）；
3. `LICENSE` 复制到 `licenses/`；
4. `package_info()` 仅提供 `includedirs=["include"]`，无 libs/bindirs（R38 纯库包无需 commands.json）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 默认按 autotools 模板生成骨架 | 构建系统探测缺 header-only 分类 | 手工按 `templates/conanfile-headeronly.py.tmpl` 生成配方（conanfile.py + conandata.yml + test_package/） |
| 2 | 上游头文件在仓库根目录而非 include/ | 上游布局如此 | package() 中从 `source_folder` 直接复制 `PerlinNoise.hpp` 到 `include/` |

## 源码修改

无（纯头文件库，未打补丁）。

## 上游测试

- 上游无注册单元测试（无 ctest/make check 套件）；仅 `example.cpp` 演示程序（生成噪声 BMP 图并断言输出）。
- test_package 消费者测试实际调用 `siv::PerlinNoise` 的 `noise2D`/`octave2D`，
  验证有限值、确定性（同种子两次调用一致）、范围 [-1,1] 与同种子跨实例一致性（R34 实质依赖）。
---

**编译结束**: 2026-09-05 21:29
**最终状态**: built

## 知识判定（executor_local_required, 官方只读快照）

- 快照: /storage/Users/currentUser/runnerljs002/perlinnoise-knowledge-snapshot-perlinnoise-3.0.0-r01-pc1-34-20260905T122859Z (ref=main, HEAD=0b458be188c0740435e57607d31384570d947f57, sparse=knowledge, 只读审计 OK)
- 扫描范围: 正式 knowledge/graph/E*.kv(544) + knowledge/doc/E*.md(540) + knowledge/drafts/*(371)
- perlinnoise 命中: 正式 0 条, 草稿 0 条; header-only 主题正式条目 E011/E099/E153/E195/E284/E309/E321 与草稿 DRAFT-ctre-3.10.0-header-only-recipe-test-package 等 18 条, 均不构成等价命中（无 perlinnoise 特有错误面）
- 候选材料: 适配全程无当前库源码/配方/测试真实首错（纯 header-only, 无补丁）; W3 JC5 误拦为其他库基线 .ci-trigger（基线噪声, 已隔离复验恢复, 禁止路径B）; gen_summary 异常为共享框架缺陷（DRAFT-cute_headers 已覆盖同类, 禁止路径B）
- knowledge_decision: path_a_no_knowledge（路径 A，无可沉淀当前库经验，不创建草稿）
