# 上游 tag 名与版本号不一致时的源码归档选择

> 草稿（DRAFT）。与同目录 `opencsg-1.8.2-upstream-tag-name-vs-version-archive-selection.kv` 成对。

## 问题

上游 tag 名**不一定等于版本号**：

- 有的用 `v1.8.2`；
- 有的用 `<name>-1-8-2-release`（点换成连字符，还带 `release` 后缀）；
- 有的带项目前缀。

照抄版本号拼 URL 会 404 或拿到错误归档。另外，Conan `get()` 按 URL 的 **basename** 推断解压器；
basename 不含 `.tar.gz` 时可能被当作 zip 解压而报 `BadZipFile`（见知识条目 E276）。

## 做法

1. **确认真实 tag 名**（用 releases/tags API 或发布页），不要用版本号臆造 URL。
   优先选官方 tag 源码归档（通常含完整测试/示例，优于 PyPI sdist）。
2. 归档 URL 的 basename **以 `.tar.gz` 结尾**；否则显式给 `get()` 传 `filename=`，
   让 Conan 选对解压器。
3. 记录 URL + tag + SHA256。CI 会把 `github.com` URL 重写为 **gh-proxy 镜像 fallback**，
   属正常行为；只要保证 `source()` 的 url/sha256 与 `conandata.yml` 一致即可。

```bash
# 确认真实 tag
curl -sL https://api.github.com/repos/<owner>/<repo>/tags | grep '"name"'
# URL 形态
#   https://github.com/<owner>/<repo>/archive/refs/tags/<real-tag>.tar.gz
```

## 证据（opencsg 1.8.2）

- 真实 tag 是 `opencsg-1-8-2-release`（连字符 + `release` 后缀），**不是** `v1.8.2`。
- 归档 URL：`https://github.com/floriankirsch/OpenCSG/archive/refs/tags/opencsg-1-8-2-release.tar.gz`
- SHA256：`63c74513f8197ceaef68bd90502c096b64146997d67e0979a82e0e8db2928527`
- `get()` 传 `strip_root=True` 与 `filename="opencsg-1.8.2.tar.gz"`；CI 日志出现
  `Uncompressing opencsg-1.8.2.tar.gz to .`，无 `BadZipFile`。
- 设备下载经 gh-proxy 镜像成功（`Sources correctly downloaded from https://gh-proxy.com/...`）。

## 适用范围

所有从 GitHub/GitLab 拉 tag 源码归档的配方，尤其是 tag 命名不规则的仓库；
以及任何依赖 `get()` 自动推断归档格式的 `source()`。
