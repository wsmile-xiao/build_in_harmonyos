# DRAFT — conandata.yml 注释中的裸仓库 URL 被 W3 pre-download 误匹配并子串改写污染

> 状态: 草稿（基于 jwt-cpp 0.7.1 R01 真实证据，待查重/提升）。
> 依据: R39 官方源铁律 + ci/conan/build_and_test.sh pre-download 正则行为。

## 真实问题（场景）

jwt-cpp 0.7.1 在 `finish`（W3）阶段 `build_and_test.sh` 的 pre-download 步骤，
把 conandata.yml 的源码 URL 下载后改写为 file:// 本地路径，随后 conan create 失败：

```
[step] Pre-download: extracting source URLs from conandata.yml...
  found 3 source URL(s)          ← 比预期的 1 个多，注释里的裸 URL 被误提取
[step] Running conan create ...
jwt-cpp/0.7.1: WARN: Could not download from the URL
  https://gh-proxy.com/file:///storage/.../predl_cache/71b60c5f_jwt-cpp/archive/refs/tags/v0.7.1.tar.gz: 403: Forbidden.
ERROR: jwt-cpp/0.7.1: Error in source() method
  NotADirectoryError: [Errno 20] Not a directory:
  '.../.build-cache/predl_cache/71b60c5f_jwt-cpp/archive/refs/tags/v0.7.1.tar.gz'
```

## 根因

conandata.yml 注释里写了裸仓库 URL：

```yaml
# Official source: https://github.com/Thalhammer/jwt-cpp (tag v0.7.1)
sources:
  url: "https://github.com/Thalhammer/jwt-cpp/archive/refs/tags/v0.7.1.tar.gz"
```

pre-download 脚本的正则 `https?://[^\s"']+` 从**全文（含注释）**提取 URL，
把 `https://github.com/Thalhammer/jwt-cpp`（仓库根）也当作源码 URL 下载；
随后 `content.replace(url, f'file://{local_path}')` 对完整归档 URL 中出现的该短子串
也做替换，把真正的源码 URL 改成畸形 `file://.../predl_cache/{hash}_jwt-cpp/archive/refs/tags/v0.7.1.tar.gz`。
conan get() 先试镜像包装 `https://gh-proxy.com/file://...`（403），再试本地畸形路径
（NotADirectoryError），conan create 失败、W3 门禁红。

## 方案

conandata.yml 注释中不写裸 http(s) URL，只保留 `sources.url` 一处的官方归档 URL + 对应
SHA-256；注释写纯文本（软件名/版本/tag 描述）即可（参考 range-v3 0.12.0 等既有库注释风格）。

```yaml
# conandata.yml — jwt-cpp 0.7.1
# 官方 tag v0.7.1；SHA-256 由官方 GitHub release 归档实测（2026-09-02）。
sources:
  url: "https://github.com/Thalhammer/jwt-cpp/archive/refs/tags/v0.7.1.tar.gz"
  sha256: "e52f247d5e62fac5da6191170998271a70ce27f747f2ce8fde9b09f96a5375a4"
```

## 验证

- 修复后 W3 复跑: `setup.sh 通过 / build_and_test.sh 通过 / JC_RESULT=pass / Junk Files: 0`，
  finish 至 `built`。
- conandata.yml 保持官方 URL + 真实 SHA-256，无 file:// / 镜像 / 本地路径残留。

## 适用边界

- 适用: 所有 conandata.yml 注释含裸 http(s) URL 且经 W3 pre-download（github 源尤甚）的库。
- 不适用: 注释不含 URL 或 pre-download 未启用（无此问题）。

## 查重

搜索范围: `knowledge/drafts/` + `knowledge/graph/` + `knowledge/doc/`
（grep `pre-download|predl|注释.*URL|file://.*改写|conandata.*comment`）。
命中:
- E333（pre-download 正则对连字符文件名截断，PyPI sdist 场景）——异根因（截断 vs 注释误匹配）。
- E299（Conan 源码获取失败分层诊断）——异主题（下载失败归因）。
- E017 / DRAFT-lexy-...e017-mirror-injection-residual-cleanup（镜像注入残留清理）——异主题
  （残留清理 vs 注释 URL 误匹配）。
**均未专门覆盖「conandata.yml 注释裸 URL 被 pre-download 误匹配并子串改写」——本草稿为新增知识，无重复条目。**