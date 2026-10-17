# kodi-game-libretro 21.0.10 适配笔记

## 源码
- 上游: kodi-game/game.libretro（Kodi "Libretro Compatibility" game client）
- tag: `21.0.10-Omega`（tag commit 3b3aa934198ccbf0c25138e10a579db1db8f4ffe）
- URL: https://github.com/kodi-game/game.libretro/archive/refs/tags/21.0.10-Omega.tar.gz
  （conandata 按 gh-proxy 优先双 URL 列表）
- SHA256: 42afe6b98a6ca7f65f06b4e88abf98ad58cf74d20397b591397b83bd4c526fc7（实测复算）
- SDK: Kodi 插件 SDK 头取自 xbmc 21.3-Omega 发布 tarball（kodi-addon-screensaver/21.0.2
  与 kodi-tools/21.3 同源）
  - SHA256: a60afcb556e4a00cb19fc35b7e77758107c9a8096c6ce9b66af5f92396be31aa
  - 只选择性提取 `xbmc/addons/kodi-dev-kit/include` 子树（约 2.8MB）

## license 复核
- LICENSE.md：GPLv2 全文（"The GNU General Public License, Version 2"）
- `game.libretro/addon.xml.in`：`<license>GPL-2.0-or-later</license>`
- 配方 license 字段：`GPL-2.0-or-later`（与 addon.xml 一致；screensaver 先例同措辞）

## 依赖分析（W0）
- 上游 CMakeLists：`find_package(Kodi REQUIRED)` + `find_package(LibretroCommon/
  TinyXML/Rcheevos REQUIRED)` + `build_addon(game.libretro LIBRETRO DEPLIBS)`；
  次级 Find 模块（FindLibretroCommon/FindRcheevos/FindTinyXML）随仓自带，Kodi
  主模块随 kodi-addon-dev 发行（registry 无，R36，同 kodi-platform/screensaver 先例）
- 上游 `depends/common/` pin（tarball 内 .txt 实测）：
  - libretro-common @ 50c15a88eb741cbe675743a282d8cc4c89421e3f
    （header-only；tarball sha256 042986fad22dc37188df7a186d17a258edfe8e552353f9b509a47418e8dfa623 实测复算）
  - rcheevos @ v9.2.0（C 静态库；tarball sha256 c8ed6ca74f905ea0c256250e46cced579922880001337e7c3d3d68179ad89d4e 实测复算）
  - tinyxml 2.6.2_2 → registry `tinyxml/2.6.2`（W0 核实在册，配方
    cmake_target_name `tinyxml::tinyxml`，with_stl 默认开 = TIXML_USE_STL，
    与上游 depends/common/tinyxml 的 -DTIXML_USE_STL 一致）
- libretro-common/rcheevos 无 conan 包 → 按上游 pin vendor 进配方（sha256 固定）
- 无 GLES/EGL 需求（video/audio 走 Kodi Game API 回调；libretro core 由
  LibretroDLL.cpp 运行期 dlopen，OHOS 原生支持）

## 适配方案

### 1. 配方自带构建入口（recipe-cmake/ 子目录，kodi-platform 三陷阱规避）
上游 `find_package(Kodi)+build_addon()` 需要 kodi-addon-dev（registry 无）。
按 DRAFT-KODI01 模式：构建入口放 `recipe-cmake/`（上游 tarball 无此目录，规避
config_source 覆盖陷阱），主配方显式 `generators = "CMakeDeps"`，test_package
消费 find_package 走 CMakeDeps。

recipe-cmake/CMakeLists.txt 复刻 build_addon 的关键语义：
- `add_library(MODULE)` + `PREFIX ""` → 产物名 `game.libretro.so`
  （addon.xml `library_filename` 期望的准确文件名）
- 上游 34 个 .cpp 源文件清单原样
- 链接 registry `tinyxml::tinyxml` + vendored `rcheevoslib` 静态库
- cxx_std_17（Kodi 21 插件 SDK 要求）
- 上游源码零修改，无 patch（conandata `patches: {}`）

### 2. Kodi SDK 头的选择性提取
conandata `sources.sdk` 记录 xbmc tarball；source() 用 download()+tarfile
只解出 `kodi-dev-kit/include` 并重排为 `kodi-sdk-include/`。

### 3. vendored 依赖的目录重排（本包特有）
源码 include 形态决定重排方式：
- `#include "libretro-common/libretro.h"`（带目录前缀）→ libretro-common
  tarball 的 include/ 子树重排为 `libretro-common-include/libretro-common/`，
  include dir 取其父目录
- `#include "rcheevos/rcheevos.h"` 等四头（带目录前缀）→ rcheevos tarball
  解到独立 `rcheevos-src/`（避免其 src/ 与插件 src/ 合并），公共头镜像为
  `rcheevos-include/rcheevos/*.h`（等价上游 depends 的 include/rcheevos 安装布局）；
  静态库用上游 depends/common/rcheevos/CMakeLists.txt 的同一源清单 +
  `-DRC_DISABLE_LUA` + POSITION_INDEPENDENT_CODE（上游 ExternalProject 同参）

### 4. versions.h 宏策略
与 screensaver 先例一致：**不定义** `BUILD_KODI_ADDON`/`ADDON_*_USED`，让
versions.h 编译完整版本表，宿主查询任何实例类型都返回正确版本串。
test_package 运行时验证 `GetTypeVersion(104)=="3.0.2"`（ADDON_INSTANCE_GAME=104，
ADDON_INSTANCE_VERSION_GAME="3.0.2"，min "3.0.0"，xbmc 21.3-Omega SDK
kodi/versions.h 实测 grep）。

### 5. 安装布局
- `lib/game.libretro.so`（Kodi 宿主按 addon.xml 部署加载的模块）
- `licenses/LICENSE.md`
- addon.xml 与 resources（icon/语言/设置）属 Kodi 宿主运行时部署面，由宿主
  集成步骤落位，本包不重复打包

## 上游测试核查（NO_UPSTREAM_TESTS discovery）

```json
{
  "conclusion": "NO_UPSTREAM_TESTS",
  "discovery_status": "EVIDENCE_COMPLETE",
  "upstream": "kodi-game/game.libretro tag 21.0.10-Omega",
  "checks": [
    {"check": "tarball tree has no test directories or test files",
     "command": "find . -iname '*test*'",
     "result": "no matches in the 21.0.10-Omega tree (34 addon .cpp/.h sources, resources, debian, cmake only)",
     "evidence_paths": ["21.0.10-Omega tarball (sha256 42afe6b98a6ca7f65f06b4e88abf98ad58cf74d20397b591397b83bd4c526fc7, full tree)"]},
    {"check": "no CMake test registration",
     "command": "grep -rnE 'enable_testing|add_test|\\.ctest' --include=CMakeLists.txt .",
     "result": "no matches; CMakeLists only declares sources, find_package and build_addon()",
     "evidence_paths": ["CMakeLists.txt"]},
    {"check": "upstream CI is build-only",
     "command": "list .github/workflows/; read azure-pipelines.yml Jenkinsfile",
     "result": ".github/workflows/ has only sync-addon-metadata-translations.yml (i18n); azure-pipelines.yml is a Windows/UWP cmake build matrix cloning xbmc Omega; Jenkinsfile is buildPlugin(version: Omega) only — no test step anywhere",
     "evidence_paths": [".github/workflows/sync-addon-metadata-translations.yml", "azure-pipelines.yml", "Jenkinsfile"]},
    {"check": "no test framework sources or fixtures",
     "command": "full tarball file listing inspection",
     "result": "src/ holds the game client itself (client/input/libretro/cheevos/settings/audio/video/log/utils); no test runner, no fixtures, no language test bindings",
     "evidence_paths": ["src/", "game.libretro/resources/"]}
  ],
  "official_test_count": 0,
  "evidence_paths": [
    "https://github.com/kodi-game/game.libretro/tree/21.0.10-Omega",
    "21.0.10-Omega source tarball (sha256 42afe6b98a6ca7f65f06b4e88abf98ad58cf74d20397b591397b83bd4c526fc7)"
  ],
  "conclusion_rationale": "上游 0 个官方测试，N=0 口径成立；test_package 按仓内惯例补消费者侧真实检查（dlopen + 入口符号 + 版本 API 断言）"
}
```

## test_package（消费者侧）
`test_game_libretro`：dlopen 打包产物 `game.libretro.so` → dlsym 三个 Kodi
二进制插件入口（ADDON_Create / ADDON_GetTypeVersion / ADDON_GetTypeMinVersion）
→ 实际调用 `ADDON_GetTypeVersion(104)`/`ADDON_GetTypeMinVersion(104)` 断言
game client 实例 API 版本 "3.0.2"（min "3.0.0"）。5 项断言。game client 无
独立运行入口、运行需 Kodi 宿主 + libretro core，headless CI 只能验证到
加载/符号/版本 API 层。

## 风险
- 实际游玩路径（dlopen libretro core、视频/音频回调）无法 headless 验证
  （需 Kodi 宿主 + 具体 core）；本包保证模块可加载、入口与 API 版本契约正确
- Cheevos（成就）运行期联网行为不在 CI 覆盖面
- device FS 大小写不敏感导致的 worktree 幽灵 dirty 条目与本包无关

---

**适配日期**: 2026-09-27
**状态**: 见版本 manifest.yaml
