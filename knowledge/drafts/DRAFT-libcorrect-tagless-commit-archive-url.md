# DRAFT：tagless 上游的 commit 归档 URL → Conan BadZipFile，用官方 GitHub archive URL 修复

> Status: **Draft**（待审核 promote）| severity: `P1` | category: `source-download, tagless` | Updated: 2026-09-27
> 对应: `knowledge/drafts/DRAFT-libcorrect-tagless-commit-archive-url.kv`
> similar_to: E276, E483

---

**触发场景**：上游库没有发布任何 git tag / GitHub release（libcorrect 即如此，
2016 建仓至今无 tag），任务版本号需取自可审计事实（libcorrect "3.5" 来自上游合入的
`cmake_minimum_required(VERSION 3.5)`，PR #50）。conandata.yml 用裸 codeload commit
URL 下载官方归档，报 BadZipFile。

## 错误签名

```text
BadZipFile: File is not a zip file
codeload.github.com/<owner>/<repo>/tar.gz/<sha>   （末段无扩展名）
```

## 错误摘录

```text
ERROR: libcorrect/3.5@ohpcd/stable: Error in source() method
        get(self, **self.conan_data["sources"], strip_root=True)
        BadZipFile: File is not a zip file
```

## 根因

上游无 git tag → 只能固定官方 commit SHA。裸 codeload commit URL
`https://codeload.github.com/<owner>/<repo>/tar.gz/<sha>` 的 URL basename 是 40 位
十六进制 commit SHA（无 `.tar.gz` 扩展名），Conan `tools.files.get()` 依据 URL basename
推断压缩格式失败，默认按 zip 解压 → BadZipFile。tarball 本身合法（`tar -tzf` 能列，
sha256 校验通过），非源码损坏。

## 推荐方案（rec_approach: `official-github-archive-url-for-tagless-commit`）

把 conandata.yml `source.url` 改为**官方 GitHub archive URL**：
```yaml
sources:
  url: "https://github.com/<owner>/<repo>/archive/<sha>.tar.gz"
  sha256: "<sha256 与裸 codeload commit 归档逐字节一致>"
```
- 以 `.tar.gz` 结尾 → Conan get() 正确走 tar.gz 解压（G2 PASS）；
- GitHub 官方 archive URL 302 重定向到 codeload 官方 commit 归档，内容逐字节一致；
- 无需改 get()（不入 `filename=` 参数），URL 保持官方源（R39）。

## 与既有条目差异（七轴）

- E276 / E483 记录的是 **codeload tag URL**（`refs/tags/v.X.Y.Z`）无扩展名，修复是在
  `get()` 显式传 `filename=`. **本条目是 tagless 场景的 commit URL**，且修复方式是
  **改 conandata URL 为官方 archive URL**（非加 filename 参数）。E483 的 fallback
  明确称 codeload URL 无法重写加扩展名——本方案证明官方 archive URL 是可加扩展名的
  官方等价形式，是该声称不可行路径的可行替代。
- 已在本轮 libcorrect 3.5 真机验证：两种 URL 下载 sha256 完全一致，G2 PASS，W3 PASS。

## 适用边界

- 无 git tag / release 的上游库（tagless）；可跨库复用。
- 非边界：有 tag 的库用普通 codeload refs/tags URL（E276/E483 场景），或浅档正常命名
  的 release tar.gz（不受影响）。

## 关系

similar_to: E276, E483；`prerequisite_of` 无；`conflicts_with` 无。

---
*本文件由 `knowledge/drafts/DRAFT-libcorrect-tagless-commit-archive-url.kv` 派生；与 libcorrect 归档同 PR 交付，待主编审核 promote 后转入 doc/。*