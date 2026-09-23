# conan global.conf 的 download_cache 不展开 $HOME（真机离线缓存静默失效）

> Draft: DRAFT-CSIG-DEVICE-DOWNLOAD-CACHE-ABS-PATH
> Stem: `c-sig-3.8-device-download-cache-abs-path` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-CSIG-DEVICE-DOWNLOAD-CACHE-ABS-PATH
- **严重度**: 2
- **类别**: conan-env-offline-cache
- **触发工具**: conan
- **阶段**: source-download

## 错误特征

```
c-sig/3.8: WARN: network: Error downloading file https://github.com/...:
  HTTPSConnectionPool(host='github.com', port=443): ... Connection to
  github.com timed out. (connect timeout=30)
c-sig/3.8: Waiting 5 seconds to retry...
ERROR: c-sig/3.8: Error in source() method, line 55  get(  ...
  ConanException: Error downloading file ...
```

（明明已经把 tarball 按 `<sha256[:2]>/<sha256>` 预置进了缓存目录。）

## 可复现问题

真机（无 GitHub 出口）隔离 `CONAN_HOME`，`global.conf` 写：

```
core.download:download_cache=$HOME/tmp/csig-dl
```

并在 `$HOME/tmp/csig-dl/50/<sha256>` 预置好源码。`conan create` 的
`source()` 阶段**忽略缓存**直连 GitHub，两轮超时后失败。把同一行改成绝对路径
`/storage/Users/currentUser/tmp/csig-dl` 后，一轮预期内的下载超时之后立刻出现
`Sources correctly downloaded from ...`（缓存命中）。

## 根因分析

Conan（实测 2.29.1-OHOS 版）把 `global.conf` 的值当**字面字符串**，不做
`$HOME`/`~` 展开：值为 `$HOME/tmp/csig-dl` 时，缓存根目录是一个字面名为
`$HOME` 的路径，与预置文件永远对不上；conan 不会报“缓存路径不存在”，而是
**静默跳过缓存**直连上游——在无外网的真机上表现为“缓存明明备了却不生效，
最后超时失败”。真机直连 GitHub 失败本身是已知环境事实（botan3 同款），
因此这个坑极易被误判为网络问题而不是配置问题。

## 解决方案

**主方案**: absolute-path-in-global-conf

1. `global.conf` 一律写**绝对路径**：
   `core.download:download_cache=/storage/Users/currentUser/tmp/<pkg>-dl`
2. 预置文件：`<cache>/<sha256[:2]>/<sha256>`，设备端 `sha256sum` 复核；
3. 判读信号：日志先出现 1 条 `WARN: network: Error downloading`，随后
   `Sources correctly downloaded from ...` = 缓存命中正常；若出现 **2 条超时 +
   `Error in source() method`** = 缓存路径写错（检查 global.conf）。

## 关联提示（同环境第二坑）

设备默认 `~/.conan2/profiles/ohos-aarch64` 是**旧版**（`cppstd=gnu14`、
`libstdc++`、无 `tools.build:compiler_executables`），与仓库 CI profile
（`cppstd=17`、`libc++`、hnp 工具链 conf）不一致。隔离构建时自带仓库 CI
profile，不要信任设备默认 profile。

## 关联条目

- E347（GitLab 418 反爬，预置 sha256 缓存绕过）：缓存预置**方法**的出处；
  本条目补充的是 **global.conf 路径写法** 这一配置层陷阱。
