# DRAFT-monocypher-4.0.2-release-vs-tag-archive：官方 release 分发物与 tag 归档内容差异的处理边界

## 问题

GitHub 项目的 **tag 归档**（`archive/refs/tags/4.0.2.tar.gz`）与**官方 release 分发物**
（`releases/download/4.0.2/monocypher-4.0.2.tar.gz`）内容并不相同。对 monocypher 4.0.2 实测：

- tag 归档中 `src/monocypher.c` / `src/monocypher.h` 的版本串是 `__git__` 占位符
  （由 `dist.sh` 在发布时替换为正式版本号），直接构建出的产物版本标识错误；
- tag 归档**不含** `tests/vectors.h`（上游测试必需的测试向量，需 libsodium 重新生成），
  `make check` 直接失败并提示“I cannot perform the tests without the test vectors”；
- 官方 release 分发物才同时携带正确版本串 `4.0.2` 与 `tests/vectors.h`，且 makefile 已
  移除 dist 相关目标（`all: library`，不再要求 doc 生成）。

## 根因

tag 归档由 git 树快照生成，未经过发布流水线处理：版本占位符未替换、发布时生成的测试
向量未包含；release 分发物是上游正式发布产物，内容完整且自洽。

## 方案

1. conandata.yml 的 sources.url 使用**官方 release 分发物 URL**（R39 官方源不变），
   例如 `https://github.com/<owner>/<repo>/releases/download/<ver>/<name>-<ver>.tar.gz`；
2. 以 release 分发物解压内容为 `.orig`/`.work` 基线（含 `tests/vectors.h`）；
3. tag 仅用于核验上游正式版本存在性（`git ls-remote --tags` 或 GitHub API），
   记录 tag commit 到 manifest 供追溯，不作为下载源。

## 验证

- `sha256sum` 核验 release tarball（`38d07179738c0c90677dba3ceb7a7b8496bcfea758ba1a53e803fed30ae0879c`）；
- `make check` 全部通过（All tests OK!，39 个测试函数 / 87 处断言）；
- 解压后 `head -1 src/monocypher.c` 为 `// Monocypher version 4.0.2`（非 `__git__`）。

## 适用边界

适用于 GitHub 项目首次适配时发现 tag 归档与 release 分发物内容不一致的库，
尤其是**测试向量 / 生成文件只在 release 打包**、或**版本串在发布时替换**的项目。
不适用于 release 与 tag 内容完全一致的简单项目；不改变 R39 官方源要求。

## 反例与限制

- 不得因 release URL 下载失败而回退到个人 fork / 非官方镜像作为正式 conandata 源；
- 不得在 patch 中硬编码替换 `__git__` 掩盖上游发布流程问题（应先换用 release 分发物）；
- 若项目没有 release asset，才考虑 tag 归档 + 明确记录缺测试向量的原因与本地补向量方式。
