# pcapfix 1.1.7 — 无外网真机的 download cache 预置法（draft）

**Category**: conan | network | ohos | ci · **Severity**: 2 · **Tool**: conan

## 症状

影子真机（LAN 10.62.178.77:2222）完全无出站网络——`curl -sI` 对 github/
codeload/gitcode/cnb.cool/gh-proxy 全部无输出；`conan create` 在 source() 下载
阶段必然失败。

## 根因与机制（conan 2.29/2.31 源码实证）

1. `tools.files.get` → `SourcesCachingDownloader`，先查
   **`core.sources:download_cache`**（不是 `core.download:download_cache`——那管
   packages 缓存；且新版无 `conan config set`，直接写 `global.conf`）。
2. 命中路径：`<download_cache>/s/<文件内容的 sha256>`（`DownloadCache.source_path`）。
3. 命中且无 backup-sources 元数据 json 时**不强制重下**（源码注释："We do not
   want to force re-downloading"），只要求 conandata 声明的 sha256 与预置文件一致。

## 对策（保持 conandata 官方 URL 不动，R39/PF7 完好）

```text
1. mkdir -p $JOB/dlcache/s；源码包放 $JOB/dlcache/s/<conandata sha256>
   （tar-over-ssh 传输，设备端 sha256sum 复核）
2. 隔离 CONAN_HOME=$JOB/conan-home：拷设备 settings.yml（OHOS 枚举），
   global.conf 写 core.sources:download_cache=<绝对路径> + tools.build:jobs=1
3. profile 用仓库 ci/conan/profiles/ohos-aarch64（push 后按文件路径引用）；
   PATH 前置 /storage/Users/currentUser/usr/local/bin:/data/service/hnp/bin；
   TMPDIR=$JOB/tmp
4. conan create → "Source ... retrieved from local download cache" → 后续与在线一致
```

## 限制

- 有依赖的包需同法预置每个依赖的源码包，或预 download 二进制——零依赖小包最划算。
- 该设备非交互 shell 无 git：conan 的 git source 类配方不可用。
- 设备内存常年 <1GB free：小包可跑，重包须错峰。

## 验证

pcapfix 1.1.7 于 LAN 机全绿（create3.log 留档设备 `$HOME/tmp/pcapfix-job/`）。
