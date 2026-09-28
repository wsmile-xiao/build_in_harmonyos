# DRAFT: 上游休眠仓库无 tag/release —— 官方 master 快照 + sha256 唯一可审计引用

## 问题描述

libclsph 2.6 任务要求从官方仓库 `https://github.com/libclsph/libclsph` 取源，但该仓库
2016-03-19 后停更、从未打 tag/release：

- `git ls-remote --tags` 返回空
- GitHub API `repos/libclsph/libclsph/tags` 返回空数组（经代理实测）
- 候选 tag tarball（`2.6`、`v2.6`、`2.6.0`、`v2.6.0`、`release-2.6`、
  `libclsph-2.6`、`2.6.tar`）全部返回 14 字节 `404: Not Found`

按版本号猜 tag 必然失败；镜像/搬运源违反 PF7 官方源约束；Debian orig 仅适用
Debian 打包过的库（cppnumericalsolvers 先例），本库不在 Debian 源池。

## 根因

- 上游项目长期休眠且发布流程缺失（从未建立 tag/release）
- 版本号（2.6）是任务/社区沿用标识，并非仓库内的 git ref

## 解决方案

1. **确认无发布**：tags API 空数组 + 多候选 tag tarball 全 404 + `git ls-remote --tags` 空，
   三者交叉确认（避免误判为网络问题）。
2. **官方 master 快照取源**：conandata `sources.url` 用
   `https://github.com/<org>/<repo>/archive/refs/heads/master.tar.gz`（官方 HTTPS，
   PF7 合规），下载后 `sha256sum` 核验并写回 conandata/manifest 固定。
3. **如实标注 provenance**：manifest 记录 `upstream_identity: invalid`（非稳定发布事实）、
   上游 HEAD（`4cdf18fba05a64826484b0db238b604c90a2e894`）与最后推送时间；notes/台账
   写明"master 快照"而非伪装成 tag 版本。
4. **版本号语义**：适配版本号保留任务给定的 2.6（适配版本标识），源码引用以 sha256 锚定，
   二者分离。

## 验证

- 下载 tarball sha256 = `1fab7ef6fcb61d7fc18d35c6200893a1e895ef9303fbec17639ae43a5c54cddb`
  与 conandata 一致
- conan-verify G2 source() 通过；构建、测试、test_package 全部基于该快照完成
- 交付 conandata/manifest 无 file://、无镜像路径、无本地缓存路径

## 适用边界

- 适用于所有无 tag/release 的休眠三方库（官方仓库仍可达）
- 反例：有正式 tag 的库必须用 tag tarball；Debian 打包过的库可优先 Debian orig
  （cppnumericalsolvers 先例）
- 未覆盖：官方仓库已删除/不可达的场景（需分析端另行安排源）

## 关联

- `similar_to`：DRAFT-cppnumericalsolvers-1.0.0-no-tag-bazel-only-debian-orig
  （触发相同：上游无 tag；方案不同：其用 Debian orig，本候选用官方 master 快照）
- `caused_by`：上游无发布习惯
- 无 `conflicts_with`
