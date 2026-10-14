# DRAFT-21004: conandata.yml 注释行含 https:// 会被 CI pre-download 误提取为源码 URL

- **来源**：lwjson 1.9.0 适配（2026-10-04）；libfixmath64 先例（2026-09）
- **相邻条目**：E333（pre-download 正则截断 PyPI 连字符 URL——同一脚本另一形态）

## 问题（一类）

`ci/conan/build_and_test.sh` 的 pre-download 步骤用多行正则
`(?:^|\s)(?:url:?\s*)?["']?-?\s*(https?://[^\s"']+)` 对 conandata.yml **原文**
直接提取 URL（MULTILINE，不识别注释）。因此 **注释行里的任何 https:// URL**
都会被当成源码 URL：

1. 被加入下载队列（下载 404 或错误内容）；
2. `content.replace(url, "file://<本地缓存>")` 全文替换时，若注释 URL 是
   真实 URL 的**前缀**，会把真实 URL 前缀一并改写成 file://（gh-proxy/file://
   复合损坏）—— conan get() 取到损坏路径，conan create 失败且极难排查。

## 规避规则（本项目铁律）

**conandata.yml 注释里绝不能出现任何 https:// URL。** 真实 URL 只放在
`sources.url` 字段；来源说明用无 URL 的短注释。

```yaml
# conandata.yml - lwjson 1.9.0          ← 注释：无 URL
# 官方 tag v1.9.0 (MaJerle/lwjson)      ← 注释：无 URL
sources:
  url: "https://github.com/MaJerle/lwjson/archive/refs/tags/v1.9.0.tar.gz"
  sha256: "fd1aae..."
```

自查命令：

```bash
grep -n 'https\?://' conandata.yml | grep -vE '^\s*sources|^\s*url:\s*"' || echo CLEAN
```

## 验证

- libfixmath64（2026-09）：注释带 URL → 被提取 + file:// 替换腐蚀真实 URL
  前缀 → conan create 失败（首个先例）；
- lwjson 1.9.0（本轮）：注释无 URL，CI pre-download 只提取到 sources.url 一个
  URL，conan create/conan-verify 全绿（规避后无该错误）。

## 适用边界

- 适用于所有写 conandata.yml 的配方；CI worker 与本机 W3 的 pre-download
  都会运行该正则，本地通过≠CI 不受影响。
- 反例：脚本路径、验证命令等非 conandata 文件中的注释 URL 不受此规则约束；
  但知识库故事（DRAFT-note）与 finalize 报告同样应避免在 conandata 关联文本中
  制造歧义。

## 与既有知识的关系（七轴查重）

| 轴 | 结论 |
|----|------|
| exact_duplicate | 否 |
| causal_duplicate | 否（E333 是 URL 截断根因：连字符括号类字符；本条是注释行提取 + 前缀腐蚀） |
| trigger_overlap | 是（同一 pre-download 脚本，trigger_overlap 承认） |
| solution_overlap | 部分（规避方案不同：E333 改 URL 形态；本条禁注释 URL + 自查命令） |
| combination_novelty | 有：注释过滤 + 前缀腐蚀机制 + 一键自查 |
| boundary_novelty | 有：注释/字段区分 + 前缀腐蚀触发条件（注释 URL 为真实 URL 前缀） |
| test_migration_novelty | 有:自查命令可入 CI 预检 |

**决策**：new_draft（DRAFT-21004）——对 E333 为 trigger_overlap + solution_overlap
部分覆盖，新增"注释提取 + 前缀腐蚀"差异并已由规避实践验证。