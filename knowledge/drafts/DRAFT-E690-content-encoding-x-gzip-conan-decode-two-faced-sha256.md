# DRAFT: Content-Encoding: x-gzip 让 Conan 算出"解码面" sha256 —— 双面 sha 的定性与两条已过审修法

- **草稿 ID**: DRAFT-E690-content-encoding-x-gzip-conan-decode-two-faced-sha256
- **来源库**: simstring 1.0（OHOS PC aarch64, conan 2.29.1 / requests + urllib3）
- **状态**: 草稿（待主编 promote 为正式 E 条目）
- **同族条目**: E299（source() 期 sha256 失败分层）、E017（镜像回退）
- **仓内先例**: blepvco 0.1.0（urllib 回退）、bsdgames-nonfree 2.17（改记解码面+双面注释）、
  libquantum 1.0.0（换无该头的权威 CDN 镜像）

## 问题（两轮采信轮同错红，确定性定式）

simstring 1.0 的采信轮连续两轮死在 G2 `source()`：

```
ConanException: sha256 hash failed for '386f5e18…f0e4171' file.
 Provided hash: 386f5e18c9a92a84eccd6caee407e28da939dd74bb68bd17912c4d918f0e4171
 Computed hash: fa0fa2969ec5be85e5752156c469ffef07fb90f4780e77d2a57beb1ccf34cdb0
```

而同一 URL：

| 客户端 | 实收字节 | sha256 |
|---|---|---|
| `curl -O`（不认 Content-Encoding） | 233446 B = 官方 .tar.gz 文件 | `386f5e18…`（== Debian `.dsc` PGP `Checksums-Sha256`） |
| python `urllib`（同上） | 233446 B | `386f5e18…`（五次复核一致） |
| **conan（requests/urllib3，透明解码一层）** | **1187840 B = 内层 plain tar** | **`fa0fa296…`** |

## 根因

chokkan.org 的静态站对 `.tar.gz` **无条件**回 `Content-Encoding`（4 形态实测）：

```
A-E: gzip           → content-encoding: gzip
A-E: identity       → content-encoding: x-gzip   ← 服务器不理会 identity
A-E: totally-bogus  → content-encoding: x-gzip
（缺省，plain curl） → content-encoding: x-gzip
body 恒为 233446B 原文件字节，content-length 恒 233446
```

HTTP 语义下"实体 = 解码后的 tar"，conan 的 `requests.Session` + urllib3
`decode_content` 是**标准行为**：`iter_content()` 吐出解码后的 plain tar，
`file_downloader.check_checksum()` 再拿 conandata 里记录的**文件面** sha 校验
→ 必然 mismatch。**两个客户端拿到两个不同但各自自洽的"正确字节"**——
是定式不是网络瞬时（两轮同值实测）。附带坑：conan 只豁免
`content-encoding == "gzip"` 的长度检查，`x-gzip` 形态还会先撞
`Transfer interrupted before complete`（blepvco 实测）。

## 三步定性（区分"网络瞬时"与"解码定式"，秒级）

```sh
# ① 解码面 sha 是否等于报错 Computed 值 —— 命中即定式
gunzip -c <文件面tarball> | sha256sum        # simstring → fa0fa296…（== Computed）
# ② 文件面自证：urllib 不认 Content-Encoding，应等于 conandata sha256
python3 -c "import urllib.request,hashlib;print(hashlib.sha256(urllib.request.urlopen('<url>').read()).hexdigest())"
# ③ 请求头能否诱导服务器不打标（simstring 不能 → 排除"改 header 可修"）
curl -sS -H 'Accept-Encoding: identity' -D - -o /dev/null <url> | grep -i content-encoding
```

## 方案（两条已过审先例，按场景二选一）

1. **先例 a（推荐，blepvco 0.1.0）——urllib 回退，保权威文件面 sha**：
   `source()` 先 `get()`；捕 `ConanException` → warning（引根因+两面 sha）→
   `urllib.request.urlopen` 拉原始字节落盘 → `check_sha256()` 兜底校验
   → `unzip(strip_root=True)` → `os.remove`。
   **选用判据**：文件面能被独立取得（curl/urllib 同值）且 conandata 已按
   官方发行物/Debian `.dsc` 锚定 —— W4/外部审查默认用 curl 复算，记文件面
   sha 才不会被判 mismatch（simstring 裁决即此：改记解码面 = 作废 W0 同源锚定
   + 自埋审计红）。
2. **先例 b（bsdgames-nonfree 2.17）——改记解码面 + 双面注释披露**：
   仅当**双 gzip**（解码一层后仍是 `.tar.gz`、拿不到原始文件字节）时成立；
   conandata sha 记 conan 落盘字节，注释同写 curl 文件面与解码面两个 sha。
   单 gzip 文件禁用（审计方 curl 复算 = 文件面 → 必判 mismatch）。
3. **先例 c（libquantum 1.0.0）**：换**无该响应头且有第二方 distinfo 佐证**的
   权威镜像 CDN —— 无镜像/无佐证时不可用（撞 PF7 源 URL 闸）。

PR 正文/notes 披露格式（可直接复用）：

```
源码 sha256 双面（Content-Encoding: x-gzip）：
- curl -O <url> && sha256sum            → 386f5e18…（文件面，conandata 记录值）
- gunzip -c <该文件> | sha256sum        → fa0fa296…（解码面 = Conan requests 栈实收字节）
```

## 影响面

- 一切"官方静态站 .tar.gz/.zip 响应带 Content-Encoding"的 conan 下载；
  设备与 CI worker 同栈同命中（worker 无 curl、CI 预下载在 OHOS 退化 conan 直连
  —— blepvco notes 实测）。
- 记哪个 sha 是**审计口径问题**不是网络问题：记错面 ⇒ W4 独立复算 mismatch ⇒
  证据链被判不一致（P0 档风险）。
