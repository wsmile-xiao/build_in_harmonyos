# DRAFT-conan-downloader-xgzip-content-encoding — conan 下载器仅豁免 Content-Encoding: gzip 的尺寸校验，对 x-gzip 透明解压源恒误报传输中断，需配方内原始字节回退下载

> **Contributor**: GoliWie | **Status**: DRAFT | **Updated**: 2026-09-05
> **Severity**: 2 | **Category**: conan / download / http-server / content-encoding
> **Audience**: 源码托管在标注 `Content-Encoding: x-gzip` 的 Apache 站点、需在配方内规避下载误报的 conan 配方作者与移植执行者

## 触发（trigger）

- 工具链：conan 下载器（`conan/internal/rest/file_downloader.py`，底层 urllib3/requests），
  `source()` 阶段（trigger_tool: conan|urllib3|get()|download；phase: source|download）。
- 服务器形态：Apache `mod_mime` 的 `AddEncoding x-gzip .gz`（`.gz` 扩展名的默认行为）——
  自建/学术/个人/老派 Apache 托管站点高发。
- 实例：blepvco 0.1.0（上游 smbolton.com）
  `https://www.smbolton.com/linux/blepvco-0.1.0.tar.gz`。

## 症状（symptom）

```
ConanConnectionError: Download failed, check server, possibly try again
Transfer interrupted before complete: 296960 < 94235
```

报错中的 A（296960）恰为解压后实际字节数，B（94235）为压缩态 `Content-Length`。
与网络质量无关，重试无效（后果详见「禁止做法」）。

## 机制（root cause）

`conan/internal/rest/file_downloader.py` 的完整性检查把下载字节数与 `Content-Length`
比较，且豁免分支写死 `response.headers.get("content-encoding") == "gzip"`
（L132 豁免判定，L135 尺寸不等且非 gzip 即 raise）：

1. urllib3/requests 按响应头声明透明解压，`x-gzip` 与 `gzip` 同等解码。
2. 从 `AddEncoding x-gzip .gz` 服务器取源时，`iter_content` 读到的是解压后字节，
   与压缩态 `Content-Length` 永不相等。
3. `x-gzip` 不落入豁免分支（豁免仅 `=="gzip"`）→ 恒定抛 `ConanConnectionError`
   "Transfer interrupted before complete: A < B"（A 恰为解压后尺寸，B 为压缩态
   Content-Length）。
4. 实测实例：`blepvco-0.1.0.tar.gz`，服务器响应 `Content-Encoding: x-gzip` /
   `Content-Length: 94235`，解压后 296960 字节 = 报错中的 A。

## 修复（rec）

推荐方案：`recipe-source-urllib-fallback`（配方内回退下载）。在 `conanfile.py` 的
`source()` 中 `try get(self, **conan_data["sources"], strip_root=True)`，捕获
`ConanException` 后用 `urllib.request.urlopen` 下载到源目录（urllib 不做
Content-Encoding 解码，原始字节落地与 Content-Length/sha256 一致），随后
`check_sha256` 校验 + `unzip(strip_root=True)` 解压并删除归档：

```python
# conanfile.py source()（示意，与 .kv rec_description 逐句对应）
try:
    get(self, **conan_data["sources"], strip_root=True)
except ConanException:
    # urllib 不做 Content-Encoding 解码：原始字节落地，与 Content-Length/sha256 一致
    # （urllib.request.urlopen 下载归档到源目录）
    ...
    check_sha256(...)              # 哈希校验兜底完整性
    unzip(..., strip_root=True)    # 解压并删除归档
```

要点：

- 哈希校验兜底完整性；回退仅在该服务器故障形态时触发，其他包/正常服务器路径不变。
- 不换镜像 URL（PF7 只允许官方源）；不让 conanfile 调外部 curl/wget（L0o）。
- 方案为通用 Python（urllib 标准库，无平台特有依赖），可直接向上游/中心仓提交（P005）。
- `rec_priority: 1`；`rec_auto_fix: false`；`rec_impl: conan-recipe-source-urllib-fallback`。

## 回退方案（fallback）

`predl-cache-warm-or-file-url`（`fallback_priority: 2`）：官方 tarball 预先 curl 落地后把
conandata.yml url 临时指向 `file://<本地缓存>`（跑完还原），或预热 conan 下载缓存。
诚实权衡：绕开了 conan 下载抽象、引入人工/CI 外部步骤、file:// 重写易残留（须跑完还原），
仅作 CI 受阻时的退路，不作为申报方案（`fallback_auto_fix: false`；
`fallback_impl: manual-predl-cache-warm`）。

## 禁止做法（forbid）

- 模式：`Content-Encoding:\s*x-gzip`（服务器响应头，非配置项）。
- 原因：仅豁免 `content-encoding=="gzip"` 的尺寸校验不会覆盖 x-gzip。
- 后果：反复重试 3 次后 `ConanConnectionError`，`source()` 失败，构建失败。

## 验证（verification）

自包含探针（不依赖任何 run 日志）：

```bash
# 1) 服务器响应头实况：期望 Content-Encoding: x-gzip / Content-Length: 94235
curl -sIL https://www.smbolton.com/linux/blepvco-0.1.0.tar.gz \
  | grep -iE 'content-encoding|content-length'

# 2) conan 豁免分支实况：期望豁免分支仅 =="gzip"
grep -n 'content-encoding' $(python3 -c 'import conan.internal.rest.file_downloader as m; print(m.__file__)')

# 3) 配方回退生效复跑：构建日志出现
#    "retrying with urllib (server responds Content-Encoding: x-gzip)" 且构建继续即为回退生效
conan create <recipe> -pr:h=<ohos-aarch64 profile> -pr:b=<ohos-aarch64 profile> --build=missing
```

## 适用边界（affected scope）

- 上游服务器对 `.tar.gz`/`.tgz` 标注 x-gzip Content-Encoding 的所有 conan 配方。
- `AddEncoding x-gzip .gz` 是 mod_mime 对 `.gz` 扩展名的默认行为，自建/学术/个人/老派
  Apache 托管站点高发。
- 普通服务器（github、GNU 镜像等）不受影响。

## 查重与关系（relations）

- similar_to: E405（OHOS 下 python subprocess 裸名命令不搜索 PATH）、
  E347（GitLab 418 拦截 conan/urllib 源码下载）。
- principles: P005（补丁必须可向上游提交）、P013（平台限制必须降级而非绕过）。
- causes / caused_by / conflicts_with / prerequisite_of: 均为空。

## 关联库

- blepvco 0.1.0（上游 smbolton.com）——本条目因其适配触发；机理本身是通用 conan 下载链
  问题，非库自身缺陷。
