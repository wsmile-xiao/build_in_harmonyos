# libdumb 2.0.3:原上游消亡项目的事实维护 fork 选源判据

> 草稿(DRAFT)— 来自 libdumb 2.0.3 HarmonyOS PC (aarch64) 适配的真实实践。
> 与 `.kv` 同 stem 配对。

## 问题

libdumb(IT/XM/S3M/MOD 解码)的原作者仓库(katajakasa)**GitHub 404**——生态
(dsda-doom、openSUSE/Fedora RPM、Kodi 插件)仍在,源却没了。conandata 源选择:

1. 原仓库 URL → 404 不可用;
2. 个人魔改 fork → 违反 R39 官方源精神;
3. **de facto 维护 fork** → 候选。

## 判据与解法

### 1. 三交叉确认 de facto fork

- **GitHub API**:`api.github.com/repos/<fork>/tags` 确认候选存在与版本序列
  (kode54/dumb:2.0.3 → 2.0.0 → 1.0);
- **下游引用面**:dsda-doom 等 CMake `find_package`/FetchContent 引用 kode54;
- **发行版打包**:openSUSE/Fedora 的 `dumb-2.0.3` RPM 出自 kode54 fork
  (opensuse.pkgs.org 可查)——发行版打包是下游引用面最大的客观证据。

### 2. conandata 用 fork 的 tag archive

CMake 项目无 autoreconf 问题(tag archive 可直接用);双源 github + gh-proxy:

```yaml
sources:
  "2.0.3":
    url:
      - "https://github.com/kode54/dumb/archive/refs/tags/2.0.3.tar.gz"
      - "https://gh-proxy.com/https://github.com/kode54/dumb/archive/refs/tags/2.0.3.tar.gz"
```

### 3. aarch64/CI 三个上游 option 全关

| option | 默认 | 处理 |
|---|---|---|
| BUILD_ALLEGRO4 | ON | **OFF**(引 allegro4) |
| BUILD_EXAMPLES | ON | **OFF**(查 argtable2/SDL2) |
| USE_SSE | ON | **OFF**(x86 旗标) |
| cmake_minimum_required | 3.1 | `CMAKE_POLICY_VERSION_MINIMUM=3.5` |

license 注意:dumb 2.0 起**重授权为 Unlicense**(非早期 GPL)。

## 覆盖判断

- `DRAFT-monocypher-4.0.2-release-vs-tag-archive`:release vs tag 内容差异;
  本条目聚焦"原上游 404 → de facto fork"的**选源主体**判据,互补。
- libzippp 7.1-1.10.1 manifest 的 ctasada→ctabin 迁移记录是该模式先例,
  但 knowledge/ 无独立条目,本条目将其抽象为通用判据。
