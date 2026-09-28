# kodi-addon-imagedecoder 21.0.2 HarmonyOS PC 移植说明

## 版本与源码

- 上游项目：<https://github.com/xbmc/imagedecoder.mpo>
- 官方标签：`21.0.2-Omega`（commit `dd589e8048c78d1efcdbb5af691ba7cf67121f81`）
- 源码包 SHA-256：`09c2466da38cc270051cd8c6df29b40628803ab4f17be5a2895c17e0e5c040b6`
- 许可证：`LICENSE.md` 为 GPLv2 全文，`imagedecoder.mpo/addon.xml.in` 声明
  `GPL-2.0-or-later` → 配方 license 字段取 `GPL-2.0-or-later`
- 上游源码补丁：无（`patches: {}`）

### 命名消歧

"kodi-addon-imagedecoder" 是 xbmc 的 imagedecoder 家族名，org 下共有
imagedecoder.mpo / raw / heif / svg 四仓。本包取 **imagedecoder.mpo**
（tag `21.0.2-Omega` 存在、依赖最简：外部依赖仅 libjpeg-turbo + tinyxml2，
无 GL/EGL；svg 无 21.0.2 tag，raw/heif 外部依赖更多）。上游 project id
`imagedecoder.mpo` 记录于 conandata/notes，交付 push gate 提请确认。

## 依赖与版本映射

| 上游 depends/common pin | ohpcd registry conan 配方 | 本包 require |
|---|---|---|
| libjpeg-turbo 2.1.1 | 3.0.4 / 3.2.0 | `libjpeg-turbo/3.2.0` |
| tinyxml2 9.0.0 | 10.0.0 / 10.1.0 / 11.0.0 | `tinyxml2/10.1.0` |

- registry 无 libjpeg-turbo 2.x / tinyxml2 9.x conan 配方，取同库最新
  registry 版本。经典 libjpeg ABI（SONAME `libjpeg.so.62`）与 tinyxml2
  C++ API 均稳定，vendored 代码仅用稳定面（jpeg decompress 结构体/函数、
  `tinyxml2::XMLDocument` 解析）。
- registry libjpeg-turbo 配方为 shared-only（`ENABLE_STATIC=OFF`），故
  插件模块保留对 libjpeg/libtinyxml2 的 DT_NEEDED（与 Kodi 发行版链接
  系统 jpeg/tinyxml2 的部署形态一致）；test_package 运行时显式前置依赖
  libdirs 到 `LD_LIBRARY_PATH` 保证 dlopen 解析。
- vendored（随上游 tarball，编入模块，无独立配方）：
  - `lib/libmpo`（C）：来自 <https://github.com/Lectem/libmpo>（
    `lib/kodi-libmpo-note.txt`：sync to 63ada10, 14 Aug 2017）。**该仓无
    LICENSE 文件、源码无 license/copyright 头**——如实注记（上游 Kodi 以
    GPL-2.0-or-later 整仓分发）。
  - `lib/TinyEXIF`（C++，MIT 风格声明，Copyright (c) 2015-2017 Seacave，
    源码头自带）：来自 <https://github.com/cdcseacave/TinyEXIF>（sync to
    6e56015, 10 Apr 2021）。

## Conan 适配

- 上游 CMakeLists 是宿主 SDK 式（`find_package(Kodi REQUIRED)` +
  `build_addon()`，随 kodi-addon-dev 发行）；registry 无 kodi 包 → 按
  DRAFT-KODI01 模式：`recipe-cmake/` 自备构建入口（经
  `build_script_folder` 消费），MODULE 目标 + `PREFIX ""` 产物
  `imagedecoder.mpo.so`（addon.xml `library_filename` 期望名），
  `cxx_std_17`；图像解码器无 GL/EGL 渲染路径，无需 HAS_GLES/GLESv3/EGL。
- vendored libmpo + TinyEXIF 源码不改动、直接编入模块（上游经
  `add_subdirectory(lib/libmpo EXCLUDE_FROM_ALL)` 产 `mpo_static` 再进
  DEPLIBS；本入口将同样 4 个 .c 源与 TinyEXIF.cpp 与插件源一起编译，
  MODULE 目标自动 PIC）。
- Kodi 插件 SDK 头经 conandata `sources.sdk` 从 xbmc 21.3-Omega tarball
  选择性提取（仅 `xbmc/addons/kodi-dev-kit/include` 子树），与
  kodi-tools/21.3、kodi-addon-screensaver/21.0.2 消费源一致。
- **不定义** `BUILD_KODI_ADDON`/`ADDON_*_USED`（DRAFT-KODI01 禁止项：
  浅文本扫描检不出实例 API USED 宏，缺宏会让 `kodi/versions.h` 版本
  switch 缺 ImageDecoder case，静默错版本）。

## 上游测试

`NO_UPSTREAM_TESTS`（discovery 证据完整，2026-09-25 对实际解包源码复核）：

- 全树无 `*test*` 文件（`find -iname '*test*'` 零命中）；
- CMakeLists 无 `enable_testing`/`add_test`/`ctest`（grep 零命中）；
- 上游 CI（`.github/workflows/build.yml`，另有 .travis.yml/appveyor.yml/
  azure-pipelines.yml/Jenkinsfile）仅装依赖 + configure + build（Debian
  路径为 debian-addon-package-test.sh 打包构建测试），无测试执行步骤。

test_package 为消费者侧真实契约检查：dlopen 打包产物、dlsym
`ADDON_Create`/`ADDON_GetTypeVersion`/`ADDON_GetTypeMinVersion` 三入口，
实际调用 `ADDON_GetTypeVersion(111)`/`MinVersion` 断言 image decoder 实例
API `3.0.1`/`3.0.0`（xbmc 21.3-Omega SDK `kodi/versions.h` 口径）。headless
无 Kodi 宿主，渲染/解码主循环依赖宿主回调（vfs OpenFile 等），无法在无
宿主环境诚实执行（P013 收缩到契约层）。

## 验证结果

见 `test_package/MANIFEST.yml` 与 run 报告（权威 CI
`ci/conan/build_and_test.sh`，profile `ci/conan/profiles/ohos-aarch64`）。
