# DRAFT-13501: 3gpp.org WAF 按 UA 过滤 + CI 预下载污染 → 大写 URL 由 conan 原生下载

## 现象

- CI `conan create` 在源码下载阶段报 `sha256 hash failed for '26104-b00.zip'`，实际下载到的
  是 ~35KB 的 HTML（title 为 "Web Application Firewall"），HTTP 200。
- 或构建中途 `unzip` 报格式错误（HTML 当 zip 用）。
- 手动 `curl -L` 默认 UA 复现拿到拦截页；浏览器 UA / Conan UA（`Conan/2.x (...)`）拿到真实文件。

## 根因

1. `www.3gpp.org`（`ftp.3gpp.org` 301 的目标）前置 WAF 按 User-Agent 过滤；
2. `ci/conan/build_and_test.sh` 的预下载用 `curl -sL`（默认 UA）→ 拿到拦截页；
   其成功判定仅 `size > 100` → 误判成功，并把 conandata.yml 中该 URL 字符串改写为
   `file://<predl_cache>/<拦截页>`（本地污染）；
3. conan 2 的 `SourcesCachingDownloader._download_from_urls` 对 URL 列表逐个尝试，
   **校验和不匹配（含 file:// 拷贝后 sha 失败）会自动回落下一个 URL**（源码实证）；
4. 预下载的 URL 抽取正则只匹配**小写** `https?://`。

## 对策（libamrnb 11.0.0.0 实证）

conandata.yml 源 URL 列表：

```yaml
- url:
    - "https://ftp.3gpp.org/Specs/archive/26_series/26.104/26104-b00.zip"   # 官方（首位，R39）
    - "HTTPS://WWW.3GPP.ORG/ftp/Specs/archive/26_series/26.104/26104-b00.zip"  # 大写绕过预下载正则
  sha256: "23df8b24b0f009783027b8eef5fa8225ec71f859f2704bdb06829f09018cc8f1"
```

- scheme+host 大写（RFC 3986 不敏感，requests/ConanRequester 正常处理），path 保持原样；
- 大写 URL 不被预下载触碰 → 由 conan 原生下载，Conan UA 过 WAF；
- 小写官方 URL 被污染时，conan 校验失败 → "Trying another mirror" → 大写 URL 拿到真包
  （本机已用 conan 真实下载器模拟该完整链路验证）。

## 验证

```sh
# conan UA 是否过 WAF（2.29.1/2.31.x 均实测通过）
python -c "from conan.internal.model.conf import Conf; from conan.internal.rest.conan_requester import ConanRequester; from conan.internal.rest.file_downloader import FileDownloader; FileDownloader(ConanRequester(Conf())).download('HTTPS://WWW.3GPP.ORG/ftp/Specs/archive/26_series/26.104/26104-b00.zip', 't.bin', retry=0); import hashlib; print(hashlib.sha256(open('t.bin','rb').read()).hexdigest())"
```

## 禁止

- conanfile 里用 curl/wget 下载（L0o）；
- `verify=False` 关校验硬过（掩盖损坏源）；
- 提交拦截页/重打包件（PF2/R39）。
