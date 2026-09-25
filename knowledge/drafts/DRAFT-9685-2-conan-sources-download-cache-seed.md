# DRAFT-9685-2-conan-sources-download-cache-seed - 真机离线源码种子的正确配置键与布局

> **Contributor**: gcw_6YxinkyD | **Status**: VERIFIED DRAFT | **Updated**: 2026-09-12
> **Source event**: bsc 2026.01 真机验证（frp 设备），issue 待补，PR #9685

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改正式知识图谱、索引或运维规则，也不声称已经
promote；是否提升及最终分类由知识库维护者和赛事评审决定。

## 适用场景

- OHOS 真机/CI worker 上验证配方，源码下载慢（GitHub 直连可达性不稳定）
  或不可达（curl TLS 证书失败 exit 60 的设备），需要**预先种子**源码到
  Conan 下载缓存实现离线/加速 `conan create`；
- Conan 2.29–2.31（OHOS 适配版同基线）。

## 问题模型

Conan 2 的下载缓存有两个不同用途的键，名字相近极易配错：

- `core.download:download_cache`：缓存**远端制品仓**（conan download）的
  工件，路径布局 `c/<url-sha256>`；
- `core.sources:download_cache`：缓存**配方 `get()` 源码下载**的备份，
  路径布局 `s/<sha256>`（源码 blob）+ `s/<sha256>.json`（URL 元数据，
  可缺省）。

配错键时**不会有任何报错**：conan 静默跳过缓存直接从 origin URL 下载。
在 GitHub 直连慢/不可达的设备上表现为 source() 阶段"长时间无输出"，极易
误判为解包慢或进程挂死（bsc 真机验证实测：配错键后 26.5MB tarball 直连
下载 ~6 分钟无日志，最终成功纯属网络恰好可达）。

## 推荐方法

1. global.conf（隔离 CONAN_HOME 下）：

   ```conf
   core.sources:download_cache=/abs/path/to/dl
   ```

   必须绝对路径（相对路径 conan 直接抛错）。同时保留
   `tools.build:jobs=1` 等隔离配置。

2. 种子布局（sha256 为 conandata.yml 里的源码校验值）：

   ```text
   <dl>/s/<sha256>          # 源码 blob，与官方 tarball 逐字节一致
   ```

   `<sha256>.json` 元数据**不需要**：无元数据时 conan 视为命中（源码已核
   对过 sha256）。

3. conan 2.31 源码依据：`conan/internal/rest/caching_file_downloader.py`
   `download()` 只读 `core.sources:download_cache`；`DownloadCache.source_path()`
   返回 `<root>/s/<sha256>`；`get_urls_from_backup_sources()` 在 json 缺失时
   返回空集 → 不触发重下载。

4. 下载种子本身可用设备可达的镜像（如 ghfast.top）：

   ```sh
   curl -L -o <dl>/s/<sha256> \
     "https://ghfast.top/https://github.com/<org>/<repo>/archive/refs/tags/<tag>.tar.gz"
   sha256sum <dl>/s/<sha256>   # 必须与 conandata 一致
   ```

## 与已有知识的差异

- `DRAFT-conandata-single-url-ci-mirror-fallback`（E549）：CI 侧镜像回退
  依赖 conandata URL **形态**（单值字符串），讲的是 CI 怎么改写 URL；本条
  是**设备侧离线种子**，讲的是 conan 怎么完全跳过下载。两者互补：CI 用
  E549，真机/离线用本条。
- `DRAFT-9359-2-ohos-device-toolchain-migration-profile`：工具链路径迁移
  （profile compiler_executables 修正）；本条是源码缓存键，同为真机隔离
  作业范式但故障表现与修法不同（那个报"找不到编译器"，这个静默直连）。

## 禁止做法

- 不要把种子放到 `<dl>/d/<sha[:2]>/<sha>` 并配 `core.download:` 键来等配方
  命中——那个键/布局属于远端工件缓存，配方 get() 根本不查。
- 不要为绕过校验篡改 conandata 的 sha256 去匹配错误下载物。
- 不要在共享 `~/.conan2` 上试验缓存键——用隔离 CONAN_HOME。

## 已验证示例

bsc 2026.01 真机验证（frp 设备，conan 2.31.1）：配错键
（`core.download:download_cache` + `d/f9/<sha>` 种子）→ 缓存未命中、
直连慢下载 26.5MB；按本条改为 `core.sources:download_cache` +
`s/<sha256>` 种子后配置正确（该轮直连已成功，种子留作复验）。
键名与布局经 conan 2.31.2 源码逐行核实（本机同版本源码）。

复现入口：

```sh
CONAN_HOME=<isolated> conan create <recipe> -pr ohos-aarch64-fixed
# global.conf: core.sources:download_cache=<dl>（绝对路径）
# 种子: <dl>/s/<conandata sha256>
```

## 证据来源

- `archives/b/bsc/2026.01/notes.md`（真机验证记录：键名修正前后行为）
- conan 2.31 源码：`conan/internal/rest/caching_file_downloader.py`、
  `conan/internal/rest/download_cache.py`
- GitCode PR #9685
