# DRAFT: Conan get() BadZipFile —— codeload URL 改写为 github archive 官方扩展名形式（tinyformat 2.3.0 实证）

> **状态**: 草稿（未审核、未合入正式知识库）
> **查重**: 同根因已有正式条目 **E483**（`BadZipFile: File is not a zip file`，主方案=显式 `filename=`）
> 与 **E276**。本稿为其**新增边界实证**：E483 fallback 断言 "codeload URL 格式固定无法加扩展名，
> 改写方案对 codeload 不适用"，本轮 tinyformat 2.3.0 实测 **codeload 可改写为
> `github.com/<owner>/<repo>/archive/refs/tags/<tag>.tar.gz` 官方扩展名形式**（同 tag 同 tar 内容、
> sha256 不变、E017 镜像注入同样生效），即 codeload 并非不可改写。新增差异已由真实日志验证、可跨库复用。

## 问题签名

- 错误日志：`ERROR: Error in source() method, line 41 ... BadZipFile: File is not a zip file`
- 触发工具/阶段：Conan `source()`（`get()` 下载并解包时），conan create / conan-verify G2
- 匹配 E483/E276 的 `error_signature`：`BadZipFile: File is not a zip file|codeload.github.com/.../tar.gz/refs/tags/...`

## 根因（与 E483/E276 一致 + 边界修正）

Conan `tools.files.get()` 按 URL basename 推断下载文件名，再按扩展名选择解压算法。
codeload.github.com 官方 tag archive URL 形如
`https://codeload.github.com/<owner>/<repo>/tar.gz/refs/tags/<tag>`，basename 为无扩展名 `<tag>`
（如 `v2.3.0`）→ `unzip()` 误判为 zip → 抛 `BadZipFile`。实际下载体是合法 gzip tar。

**边界修正（本稿新增）**：E483 fallback_approach 注明 "codeload.github.com 的 URL 格式固定无法加扩展名，
改写方案仅适用于可重写 URL 的场景"。实测表明：GitHub 同一 tag 归档存在两种官方访问形式——
- `https://codeload.github.com/<owner>/<repo>/tar.gz/refs/tags/<tag>`（basename 无扩展名 → 误判）
- `https://github.com/<owner>/<repo>/archive/refs/tags/<tag>.tar.gz`（basename 带 `.tar.gz` → 正确识别）

两者内容（tar 字节流）与 sha256 完全一致，因此**改写 URL 即可**，无需改 `get()`/`filename=`，
无需改 sha256，配方零改动。conan-verify 的 E017 GitHub URL 镜像注入逻辑对 `github.com/.../archive/...` 形式同样生效。

## 本库真实证据（tinyformat 2.3.0, c42f/tinyformat）

| 项目 | 值 |
|------|-----|
| 官方仓库 | https://github.com/c42f/tinyformat |
| 官方标签 | `v2.3.0` |
| 原 codeload URL（失败） | `https://codeload.github.com/c42f/tinyformat/tar.gz/refs/tags/v2.3.0` |
| 改写后 URL（成功） | `https://github.com/c42f/tinyformat/archive/refs/tags/v2.3.0.tar.gz` |
| 归档 SHA-256 | `ecba2fbbd3829002a63e141b77b9f1fc30e920962f68466b50c3244652d69391`（两种形式一致） |
| 归档格式 | tar.gz（gzip，26,121 字节 codeload 下载验证） |

### 现象复现（修复前）

```bash
conan create archives/t/tinyformat/2.3.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing
# ERROR: Error in source() method, line 41
#   get(self, **self.conan_data["sources"], strip_root=True)
#   BadZipFile: File is not a zip file
```

### 修复（本轮实际采用）

```yaml
# conandata.yml
sources:
  url: "https://github.com/c42f/tinyformat/archive/refs/tags/v2.3.0.tar.gz"
  sha256: "ecba2fbbd3829002a63e141b77b9f1fc30e920962f68466b50c3244652d69391"
```

### 验证（修复后）

```bash
python3 scripts/ohc-run.py conan-verify tinyformat 2.3.0   # G2 PASS，exit 0
# 日志: archives/t/tinyformat/2.3.0/reports/conan-create.log
# 随后 finish W3 build_and_test.sh（incremental 模式）L0/L1/L4 全绿
```

## 两个可选方案对比

| 方案 | 修改点 | 适用 |
|------|--------|------|
| **URL 改写（本稿）** | conandata.yml 一处 | 上游在 GitHub、可用 archive/refs/tags/<tag>.tar.gz 形式 |
| filename= 显式传参（E483 主方案） | conanfile.py source() 一处 | codeload URL 必须保留（如依赖 E017 镜像原样形态） |

## 适用边界与反例

- 适用：source() 用 `get(self, **self.conan_data["sources"], strip_root=True)`、conandata URL 为
  codeload tag archive 的配方（任何 GitHub 托管库可跨库复用）。
- 反例：非 GitHub 托管、无 archive/refs/tags 等价形式、或必须保留 codeload 形态（依赖镜像改写）时，
  用 E483 的 `filename=` 方案。

## 关系字段

- `similar_to`: E483, E276, E569, DRAFT-dr_wav-0.13.17-codeload-archive-mime
- `caused_by`: E483（本稿为其 fallback 边界的实证修正）
- `conflicts_with`: 无（两方案互为等价可选）