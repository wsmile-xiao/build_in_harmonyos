# DRAFT-dmc_unrar-1.8.0-conan-source-cache-json-metadata：conan 源下载缓存预置必须配套 `<sha256>.json` 元数据，否则强制回源重下

> Contributor: AtomCode | Status: Draft | Updated: 2026-09-21
> Source: dmc_unrar 1.8.0 适配（github.com 主站不可达，离线跑通 W3/conan-verify）
> 对应：`knowledge/drafts/DRAFT-dmc_unrar-1.8.0-conan-source-cache-json-metadata.kv`

## 现象

按 E347 的做法预置 conan 源下载缓存（`core.sources:download_cache/s/<sha256>` 放入
curl 下载的官方 tarball），跑 `conan create` 时 source() 依旧回源下载并失败：

```console
WARN: The requested URL(s) are not listed in backup-sources metadata for this SHA256 cache
      entry. This may be a mistake, or the same checksum reused for a different upstream
      version. Re-downloading to verify.
WARN: file '.../s/9800526d...' already exists, overwriting
ERROR: network: Error downloading file https://github.com/...: Max retries exceeded ...
```

## 根因

conan 2.x 的源下载缓存（`core.sources:download_cache`）按 **sha256 键控**存放 tarball
（`<cache>/s/<sha256>`），但每个缓存条目的 **URL 归属记录在同目录 `<sha256>.json`** 的
`references` 字段。只有 tarball 而没有 .json（或 .json 的 references 不含本次请求的 URL）
时，conan 判定"缓存条目与该 URL 无对应关系"，强制回源重下以核验——离线或上游主站
不可达时直接失败。

## 修复（已验证）

预置缓存时**同时写两份文件**：

```bash
CACHE=/storage/Users/currentUser/tmp/conan-src-cache
SHA=<conandata.yml 中的 sha256>
curl -sSL -o $CACHE/s/$SHA "https://codeload.github.com/.../v1.8.0.tar.gz"
cat > $CACHE/s/$SHA.json <<EOF
{"references": {"dmc_unrar/1.8.0@ohpcd/stable": ["https://github.com/.../archive/refs/tags/v1.8.0.tar.gz"]}, "timestamp": $(date +%s)}
EOF
```

关键点：
- 文件在 `<cache>/s/` 下，`<sha256>` 是 tarball 的 SHA-256（与 conandata.yml 一致）；
- `.json` 的 `references.<ref>.url` 数组**必须包含** conanfile.py source() 将要请求的
  URL（官方 URL；可追加 ghfast.top 镜像前缀条目）；ref 键一般填 `<pkg>/<ver>@ohpcd/stable`；
- 可先观察 cache 目录下既有 `<sha256>.json` 的真实格式照抄（该目录全机器共享）；
- 缓存键是 sha256 与 URL 无关——同一 tarball 可服务官方 URL 与镜像 URL。

与 E017/E415（conandata 临时 ghfast 镜像注入 + 逐字节恢复）互补：本地 W3 走缓存预置，
CI 走镜像注入，两路都不改 conandata.yml 的官方 URL（R39）。

## 验证

dmc_unrar 1.8.0：仅放 tarball → conan create 回源失败（github.com ConnectTimeout）；
补 `<sha256>.json` 后 conan create 命中缓存离线成功，conan-verify G2 PASS（含
test_package 1/1）。

## 适用边界

- conan 2.29.1 实测；若缓存条目 .json 已含请求 URL 或网络可达则无需此步；
- 属 E347 的边界补全（E347 未记录 .json 配对要求），两者并用为完整方案。