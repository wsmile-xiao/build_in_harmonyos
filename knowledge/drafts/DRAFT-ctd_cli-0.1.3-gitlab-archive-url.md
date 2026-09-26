# DRAFT: GitLab 源下载必须用 /-/archive/<tag> 归档地址

## 现象

```text
ℹ️ 下载: https://gitlab.com/slavic-demons/korgorusze/compile_time_defined_cli
❌ 下载内容是 HTML
EXIT=3
```

GitLab 仓库主页 URL 返回的是 HTML 渲染页；把它直接当归档下载地址
（init-build --url / conandata.yml sources.url）必失败。

## 根因

GitLab 的可下载归档必须走 `/-/archive/` 路由：

```text
https://gitlab.com/<owner>/<repo>/-/archive/<tag>/<repo>-<tag>.tar.gz
```

第二个坑：**release tag 常带 `v` 前缀，与版本号不一致**。ctd_cli 0.1.3 的 tag
实为 `v0.1.3`：`curl -I .../archive/0.1.3/...` → 404，`v0.1.3` → 200。

## 修复

1. 先用 GitLab API 确认真实 tag 名（不要猜）：
```bash
curl "https://gitlab.com/api/v4/projects/<owner>%2F<repo>/repository/tags"
```
2. 归档 URL 使用 tag 全名（含 v 前缀），写入 conandata.yml sources.url：
```yaml
sources:
  url: "https://gitlab.com/<owner>/<repo>/-/archive/v0.1.3/<repo>-v0.1.3.tar.gz"
  sha256: "…"
```

## 验证

ctd_cli 0.1.3 实证：tag API 返回 `v0.1.3`；归档地址下载成功，
sha256 核验（33f908c2bb6dce23d2f5c3f4997e8a388867756b2c35b4d500c3add88bb98566）
通过；conan source() + 构建 + test_package 全绿。

## 适用边界

- 适用：以 GitLab 为官方源的全部三方库适配（含 conandata.yml 编写与 init-build 参数）。
- 不适用：GitHub（codeload / releases 附件可直接下载）、GitLab releases 附件 URL
  （/-/releases/.../downloads/...，可直接下载但通用性差）。

## 查重关系

- similar_to: DRAFT-8543-conandata-comment-url-predl-rewrite（仅 URL 话题相关：
  该条目讲 conandata 注释 URL 被 CI 预下载改写，本条目讲 GitLab 归档 URL 格式，互不重叠）。