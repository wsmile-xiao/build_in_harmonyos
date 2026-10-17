# DRAFT — conandata.yml 注释 URL 前缀被 W3 pre-download 子串替换污染 sources 归档 URL

> 状态: 草稿（基于 ring-span-lite 0.7.0 R01 finish W3 真实证据，查重未命中 → 路径 B 候选）。
> 触发: ring-span-lite 0.7.0 R01（pc1-22，2026-09-02）。
> 查重: 正式知识 E333/E415/E299、草稿 DRAFT-lexy 均为部分覆盖，未命中「注释 URL 子串替换污染」机制。

## 真实问题（场景）

`finish` 的 W3 本地 CI（`ci/conan/build_and_test.sh`）在 conan create 前运行 pre-download 脚本，
它从 `conandata.yml` **全文**（正则 `(?:^|\s)(?:url:?\s*)?["']?-?\s*(https?://[^\s"']+)`）
提取所有 URL——**包括注释行**。随后对每个提取到的 URL 执行子串替换：

```python
content = content.replace(url, f'file://{local_path}')
```

当 `conandata.yml` 注释行包含的仓库根 URL 恰好是 `sources.url`（归档 URL）的**前缀**时：

```yaml
# 上游: https://github.com/nonstd-lite/ring-span-lite      ← 注释（根 URL）
sources:
  url: "https://github.com/nonstd-lite/ring-span-lite/archive/refs/tags/v0.7.0.tar.gz"
  sha256: "..."
```

replace 会把归档 URL 的前缀段替换为本地缓存文件路径，生成：
`file://.../predl_cache/aa9b1897_ring-span-lite/archive/refs/tags/v0.7.0.tar.gz`
（把缓存文件当目录拼路径）。conan create 的 `source()` 阶段随即报错：

```
ERROR: ring-span-lite/0.7.0: Error in source() method
NotADirectoryError: [Errno 20] Not a directory:
  '.../predl_cache/aa9b1897_ring-span-lite/archive/refs/tags/v0.7.0.tar.gz'
```

同时注释 URL 本身（返回 HTML 页，size>100 字节）被 pre-download 误判为"下载成功"，
向 `.build-cache/predl_cache/` 写入坏缓存条目，进一步掩盖根因。

## 根因

1. **pre-download 的 URL 提取不区分注释与真实配置**：正则从整份 conandata.yml 提 URL，
   注释行（尤其「上游: <仓库主页>」）会被当成源码 URL。
2. **子串替换不做边界匹配**：`content.replace(url, ...)` 把「仓库根 URL」这一前缀
   也替换进「归档 URL」内部，破坏 URL 结构（文件名被当目录拼接到路径里）。
3. **错误形态误导**：报错为 `NotADirectoryError`/predl_cache 路径，易被误诊为
   网络下载失败（E299/E017 类），实际是本地改写污染。

## 方案

1. **治本（配方侧）**：`conandata.yml` 注释不要书写与 `sources.url` 存在前缀关系的
   仓库根 URL（或任何会被 pre-download 提取的 URL）；只保留官方完整归档 URL 单值 + sha256。
   上游地址信息写入 `manifest.yaml`/`notes.md`（不被 build_and_test.sh 扫描）。
2. **清理残留**：若已产生坏缓存条目，删除 `.build-cache/predl_cache/*_<repo>` 后重跑
   finish W3；严禁把 `file://` 形态的 conandata.yml 提交（破坏 R39 官方源约束、CI 无法复现）。

## 验证

- 修复前：`finish ring-span-lite 0.7.0` W3 RC=2，conan create `NotADirectoryError`（predl_cache 路径）。
- 修复后：删除注释中的仓库根 URL → `finish` W3 RC=0，`.ci-result.json` exit_code=0，
  `w3-local-ci.log` `Pass rate: 100.0% (1/1)`；conandata.yml 保持官方 URL 单值（无 gh-proxy/file:// 残留）。

## 适用边界

- 所有 conandata.yml 注释含「仓库主页/上游 URL」且该 URL 是 sources 归档 URL 前缀的 Conan 配方；
- 本地 W3 与 CI 均受影响（CI 的 build_and_test.sh 同款 pre-download 逻辑）；
- 与库类型无关（header-only / 编译库通用）。

## 查重差异

| 条目 | 覆盖点 | 差异（本候选新增） |
|------|--------|--------------------|
| E333（PyPI 连字符截断） | pre-download 正则字符类排除 `-` 导致 URL 截断 | 本候选是「注释 URL 被提取 + 子串替换污染归档 URL」，非字符类截断 |
| E415（镜像 fallback 改写恢复） | CI 把官方 url 改写为 gh-proxy 列表且不恢复 | 本候选是 pre-download 的 file:// 替换污染，非镜像列表改写 |
| E299（source 下载分类） | 网络/URL/SHA256 失败分层诊断 | 本候选是本地改写污染（非网络问题），错误形态为 NotADirectoryError |
| DRAFT-lexy（E017 残留清理） | ghfast-bak/orig 残留识别与清理 | 本候选是注释 URL 前缀污染机制，非 E017 镜像注入残留 |