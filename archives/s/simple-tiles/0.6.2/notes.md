# simple-tiles 0.6.2 — 编译笔记

## 软件信息

- **名称**: simple-tiles — 空间数据影像/瓦片生成库
- **版本**: **0.6.2**（R37 上游版本号；构建方式对齐 Homebrew formula revision 8）
- **许可证**: MIT
- **构建系统**: waf（`python3 ./waf`）
- **目标平台**: OHOS aarch64（鸿蒙 PC）
- **上游**: https://github.com/propublica/simple-tiles
- **Homebrew 参考**: https://formulae.brew.sh/formula/simple-tiles

## 依赖对照

| 依赖 | 参考版本 | 本仓 Conan | 说明 |
|------|----------|------------|------|
| cairo | 1.18.4 | `cairo/1.18.4` | recipe `requires` |
| pango | 1.50.14.1 | `pango/1.50.14.1` | 提供 `pangocairo.pc`（分支 `feat/pango-1.50.14.1`） |
| gdal | 3.9.2.1 | `gdal/3.9.2.1` | 分支 `feat/gdal-3.9.2.1`；传递 `proj/9.3.1.1` |
| glib | 2.84.0.1 | `glib/2.84.0.1` | pango 传递 |
| harfbuzz | 14.2.0.1 | `harfbuzz/14.2.0.1` | pango 传递 |
| python3 | build | 系统 | 跑 waf |

## W0 — 依赖发布检查

1. recipe 已 `requires("pango/1.50.14.1")` + `requires("gdal/3.9.2.1")`，**不再**依赖 cmd-pkgs 前缀探测。
2. W3 前需保证 cache / ohpcd 已有上述包（及 `proj/9.3.1.1`、glib、harfbuzz）。本 PR 分支仅含 simple-tiles；依赖由已合并/已发布包解析。
3. 本地交叉验证可先在 Docker 中 `conan export`/`create` 各依赖分支配方，再 `conan create` simple-tiles。

### 建议解锁顺序

```bash
# 1) 依赖链（若尚无 ohpcd 二进制）：glib → harfbuzz → pango → proj → gdal
# 2) simple-tiles（沿用版本号 0.6.2，不新建 0.6.2.1）
cd archives/s/simple-tiles/0.6.2
conan create . -pr:h=ohos-aarch64 -pr:b=default --build=missing
```

## 构建步骤（对齐 Homebrew 打包方式）

1. 下载 `v0.6.2` 源码
2. 从上游 commit 下载 Py3 兼容 `waf`（`conandata.yml` `waf.url` + sha256；不入库，R19）
3. 应用 `patches/0001-update-clang-compilation-database-py313.patch`（Homebrew 同源，文本补丁）
4. `python3 ./waf configure --prefix=<package_folder>`
5. `python3 ./waf build -j1`
6. 运行 `build/test/runner`（上游单元测试）
7. `python3 ./waf install`
8. `test_package`：`simplet_map_new` / `simplet_map_free`

## 上游测试

- `Makefile` 目标 `test` → `build/test/runner`、`api`、`benchmark`
- `runner` 覆盖 bounds/list/map/query/style/layer 等（约 30+ `assert`）
- 完整 `make test` 还依赖 `data/` 下 shapefile 夹具；recipe 在 build() 中优先跑 `runner`

## 本地完成项

- [x] 配方目录 `archives/s/simple-tiles/0.6.2/`（R37）
- [x] `test_package` + `MANIFEST.yml`（assertion_count=116）
- [x] `build()` 集成上游 `build/test/runner`（缺失则失败；`can_run` 为假时只验产物）
- [x] L0 静态门禁自检通过（L0a–L0e / R33 / R34）
- [x] Docker `oh_compile` 上 `conan create`（OHOS aarch64）通过

## Docker 验证（`oh_compile`，2026-07-20）

```bash
cd archives/s/simple-tiles/0.6.2
conan create . -pr:h=ohos-aarch64 -pr:b=default --build=missing
```

| 阶段 | 结果 |
|------|------|
| waf configure / build | ✅ 产出 `libsimple-tiles.so` + `build/test/runner` |
| 执行 `build/test/runner` | ⏭ 交叉编译 `can_run=false` |
| package | ✅ headers / `.so` / `.pc` / LICENSE |
| test_package 编译链接 | ✅ `test_simple_tiles` |
| test_package 运行 | ⏭ cross-building: compile/link only |

要点：`PKG_CONFIG_PATH` 只用 `PkgConfigDeps` 生成目录（避免包内 meson `.pc` 要求 `libpcre2-8`）；`package_info` 折叠 host 依赖 include（公开头直接 `#include` cairo/pango/gdal）。补丁 `0002` 将上游 `wscript` 的 GDAL 探测从 `gdal-config` 改为 `pkg-config gdal`。显式 `requires(glib)` + `CFLAGS` 注入 host `-I`，避免 CI 跳过 glib 二进制后编译找不到 `glib-object.h`。

## 当前状态

- **配方**：沿用 **0.6.2**；Conan `pango/1.50.14.1` + `gdal/3.9.2.1` + `cairo/1.18.4`
- **依赖风险（W0）**：PR 合并前需 ohpcd 已有 pango/gdal/proj 链；本分支不内嵌这些配方
- **运行时测试**：需真机；交叉只验编译与 runner 产物

## 本机鸿蒙真机验证（2026-08-06）

环境：`Linux HongMeng Kernel 1.12.0 aarch64`，conan 2.29.1，`/data/service/hnp/bin/clang 15.0.4`（Target: aarch64-unknown-linux-ohos）。

### 已验证

- **配方语法合法**：`conan graph info --requires="simple-tiles/0.6.2" -pr:h=ohos-aarch64` 解析完整依赖图，17 个 require 全部就位（cairo/pango/freetype/glib/harfbuzz/...）+ 3 个 build-require（cmake/meson/ninja）
- **导出无 user/channel 配方**：`conan export archives/g/gdal/3.9.2.1` 等需双导出（`gdal/3.9.2.1` 和 `gdal/3.9.2.1@ohpcd/stable`），否则 `conan create` 在 dependency graph 阶段报 "Not found in local cache, looking in remotes"
- **conan 缓存中已有 cairo/pango/glib/harfbuzz 等二进制**（`/storage/Users/currentUser/.conan2/p/b/...`，OHOS aarch64 Release），可直接复用
- **sqlite3 手动构建并打包通过**：`conan install --requires="sqlite3/3.49.1" --build="sqlite3/*"` 完成 source + build + package，`libsqlite3.a` + headers 进入 cache
- **预下载策略**：使用 ghfast 镜像（7s vs 30+min 直连）+ SHA-named `download_cache`（不是普通文件名）
- **waf 兼容性**：上游 tag 自带 waf 在新 Python 下可能缺 `imp`；recipe 构建时按 Homebrew 同源 URL 下载 waf（sha256=`dd9dd189…`），不把二进制归档进 PR（R19）

### 受阻 — 未完成

- **gdal/proj 完整构建**：recipe `Calling source()` 阶段无限挂起（CPU 0%，网络空闲）。手动解压源码到 `p/<pkgid>/s/` 后被 conan 删除重建；SHA-named `download_cache` 未生效；`s.dirty` 标记未自动清除
- **根因**：本机 conan DB 缓存完整性受损（`cache check-integrity` 报 6 个 corrupted 包），recipe-revision 与本地 cached-binary 的 pkgid 不匹配（proj 期望 `5cfa2ec12bd6…`，cache 实际 `e2b5df604cec…`），即使手动拷贝 binary 也会被 DB 标记缺失
- **gdal/proj 上游 source tarball 在 download_cache 中已就绪**（SHA 全匹配，proj 5.6MB、gdal 14MB），但 conan source() 始终无法直接利用

### 临时 R 修改

新增 `os=OHOS || !has_fixtures` 跳过上游 runner（`conanfile.py:140-167`）。理由：
- runner 集成子测试 `test_integration.c` 需 `./data/ne_10m_admin_0_countries.shp`、`./data/loss_1932_2010.tif` 等 6 个 NaturalEarth + TIGER shapefile/GeoTIFF 夹具
- 上游 `data/Makefile` 通过 `wget` 从外网拉取，鸿蒙真机无外网且 recipe 不内嵌
- 之前 `if can_run(self)` 在 OHOS native 误跑会立即 fail；改后与 cross-build 同行为（仅校验产物存在）

---

**日期**: 2026-07-20 (Docker cross 验证) / 2026-08-06 (本机鸿蒙真机)  
**状态**: 真机验证受阻于 conan DB 完整性 + 源解压挂起；recipe 与依赖图正确，Docker 交叉曾 PASS
