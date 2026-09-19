# DRAFT-fastnoiselite-1.1.1-e017-codeload-ghfast-403：E017 镜像注入把 codeload.github.com 误判为 github.com → ghfast 403 → BadZipFile

> Contributor: pc4-7 | Status: Draft | Updated: 2026-09-19
> Source: fastnoiselite 1.1.1 适配（Path B 知识库扩展）；触发场景：conan-verify G2 报 `BadZipFile: File is not a zip file`
> 对应：`knowledge/drafts/DRAFT-fastnoiselite-1.1.1-e017-codeload-ghfast-403.kv`

## 现象

`ohc-run.py conan-verify <lib> <ver>` 的 G2（conan create）失败：

```text
ERROR: Error in source() method, line 32
	get(self, **self.conan_data["sources"], strip_root=True)
	BadZipFile: File is not a zip file
```

conan-create.log 显示下载实际经镜像注入：

```text
🔧 E017 预防: GitHub URL 已临时注入 ghfast.top 镜像
Sources correctly downloaded from https://codeload.github.com/Auburn/FastNoiseLite/tar.gz/refs/tags/v1.1.1
```

对注入后 URL 直接探测：

```text
curl -s "https://ghfast.top/https://codeload.github.com/Auburn/FastNoiseLite/tar.gz/refs/tags/v1.1.1"
→ HTTP 403, body "Invalid input."
```

即 Conan 下载到的是 403 错误文本，解压必然 BadZipFile。

## 根因

`scripts/ohc/conan_verify.py` 的 E017 预防逻辑（约 561-576 行）：

```python
if "github.com" in _original_conandata and "ghfast.top" not in _original_conandata:
    modified = _original_conandata.replace(
        "https://github.com", "https://ghfast.top/https://github.com")
```

它把**任何包含 `github.com` 子串**的 URL 都注入 `ghfast.top/https://` 前缀。
`codeload.github.com` 也匹配该子串 → 注入为
`https://ghfast.top/https://codeload.github.com/...`。
但 ghfast.top 是 GitHub 内容代理，不能代理 codeload 下载域（实测 403）。

**与 E276 的区别**：E276（`BadZipFile` + codeload）根因是 Conan `get()` 按
`os.path.basename(url)` 推断文件名，codeload URL stem 无扩展名 → 误走 unzip。
本候选根因是 **E017 注入规则误匹配域名**；即使显式传 `filename=`（E276 方案），
在 E017 注入启用时下载环节就已 403，不会进入解压环节。

## 修复（已验证）

conandata.yml 源 URL 改用官方 **github archive** 形态：

```yaml
sources:
  url: "https://github.com/Auburn/FastNoiseLite/archive/refs/tags/v1.1.1.tar.gz"
  sha256: "8b1d439af1ae88eaf8d3d0838540796dfc92ddd216230b2816f0c5bcbb3c9824"
```

- 仍为 R39 官方源（github.com 官方域名）
- E017 注入后为 `https://ghfast.top/https://github.com/...archive/refs/tags/v1.1.1.tar.gz` → 实测 **200**
- 与 codeload 直连内容**逐字节一致**：SHA-256 同为 `8b1d439a…`，`diff -rq` 为空
- 改后 conan-verify G2/G3/G4 + L2/L4/L5 全通过，test_package 1/1 Passed

## 适用范围

任何 conandata.yml 使用 `codeload.github.com/<owner>/<repo>/tar.gz/refs/tags/<tag>`
形态 URL、且本地 conan-verify 走 E017 镜像注入的配方。

## 边界 / 反例

- github.com 的 release / archive 形态 URL 不受影响（ghfast 可代理）
- 未启用 E017 注入的环境（如 CI 侧有独立下载策略）可继续用 E276 的 `filename=` 方案
- 禁止把 codeload URL 手写成 `ghfast.top/https://codeload.github.com/...`（必 403）

## 关系

- caused_by: E017（镜像注入规则）
- similar_to: E276 / E392 / E483（codeload + BadZipFile 族，根因不同）
- 适用原则: R39（源码 URL 必须为官方源）
