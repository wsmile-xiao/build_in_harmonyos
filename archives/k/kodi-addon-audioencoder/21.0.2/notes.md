# kodi-addon-audioencoder 21.0.2 HarmonyOS PC 移植说明

## 版本与源码

- 上游项目：<https://github.com/xbmc/audioencoder.wav>
- 官方标签：`21.0.2-Omega`（commit `eddc36df29d1d0185eca2813c0bbf56723c45a7d`）
- 源码包 SHA-256：`2bbc3e15706e02bbd3e6be3c232522e2091509a6fdf88d8af5db4cd6bf7b3476`
  （本机与设备侧独立下载复核一致；gh-proxy 镜像路径实测可用）
- 许可证：`LICENSE.md` 为 GPLv2 全文，`audioencoder.wav/addon.xml.in` 声明
  `GPL-2.0-or-later` → 配方 license 字段取 `GPL-2.0-or-later`
- 上游源码补丁：无（`patches: {}`）

### 命名消歧

"kodi-addon-audioencoder" 是 xbmc 的 audioencoder 家族名，org 下共有
audioencoder.wav / vorbis / lame / flac 四仓，官方 tag 均为
`21.0.2-Omega`（addon.xml.in 内 `version="21.0.2"` 对应）。本包取
**audioencoder.wav**（四候选中依赖最简：单翻译单元 `src/EncoderWav.cpp`、
上游 `DEPLIBS` 为空、零外部编解码库、无 GL/EGL；备选次序 vorbis >
lame > flac，均引入外部编解码库依赖）。上游 project id
`audioencoder.wav` 记录于 conandata/notes，交付 push gate 提请确认。

## 依赖与版本映射

| 上游 depends/common pin | ohpcd registry conan 配方 | 本包 require |
|---|---|---|
| （无——DEPLIBS 为空，无编解码库） | — | 无（仅 Kodi 插件 SDK 头） |

- `audioencoder.wav` 只 include `kodi/addon-instance/AudioEncoder.h` 与
  `stdio.h`/`string.h`，编码数据经宿主回调（VFS Write/Seek）写出，无任何
  外部库 DT_NEEDED —— 比 imagedecoder 先例（libjpeg-turbo/tinyxml2）更简。
- Kodi 插件 SDK 头经 conandata `sources.sdk` 从 xbmc 21.3-Omega tarball
  选择性提取（仅 `xbmc/addons/kodi-dev-kit/include` 子树），与
  kodi-tools/21.3、kodi-addon-screensaver/21.0.2、kodi-addon-imagedecoder/21.0.2
  消费源一致（sha256 `a60afcb556e4a00cb19fc35b7e77758107c9a8096c6ce9b66af5f92396be31aa`）。

## Conan 适配

- 上游 CMakeLists 是宿主 SDK 式（`find_package(Kodi REQUIRED)` +
  `build_addon(audioencoder.wav WAV DEPLIBS)`，随 kodi-addon-dev 发行）；
  registry 无 kodi 包 → 按 DRAFT-KODI01 模式：`recipe-cmake/` 自备构建入口
  （经 `build_script_folder` 消费），MODULE 目标 + `PREFIX ""` 产物
  `audioencoder.wav.so`（addon.xml `library_filename` 期望名），
  `cxx_std_17`；音频编码器无 GL/EGL 渲染路径，无需 HAS_GLES/GLESv3/EGL。
- **不定义** `BUILD_KODI_ADDON`/`ADDON_*_USED`（DRAFT-KODI01 禁止项）。
  本轮在 xbmc 21.3-Omega `kodi/versions.h` 头层面直接核实了该陷阱机理：
  AudioEncoder 的版本 switch case 被
  `#if !defined(BUILD_KODI_ADDON) || defined(ADDON_INSTANCE_VERSION_AUDIOENCODER_USED)`
  保护——直觉定义 `BUILD_KODI_ADDON` 会让 103 case 缺失、
  `ADDON_GetTypeVersion(103)` 返回空，编译期零报错。test_package 在运行时
  断言 `ADDON_GetTypeVersion(103)=="3.0.0"`、`MinVersion(103)=="3.0.0"`。
- E092：配方经 CMakeToolchain 显式 `CMAKE_SYSTEM_NAME=Linux`
  （kodi-platform/20250416 先例）。

## 上游测试

上游（audioencoder.wav 21.0.2-Omega）无任何测试注册，证据如下
（2026-10-06 对实际解包源码复核；门禁判定留待后续阶段）：

- 全树无 `*test*` 文件（`find -iname '*test*'` 零命中）；
- CMakeLists 无 `enable_testing`/`add_test`/`ctest`（grep 零命中）；
- 上游 CI（`.github/workflows/build.yml`，另有 .travis.yml/appveyor.yml/
  azure-pipelines.yml/Jenkinsfile）仅装依赖 + configure + build（Debian
  路径为 debian-addon-package-test.sh 打包构建测试），无测试执行步骤。

test_package 为消费者侧真实契约检查：dlopen 打包产物、dlsym
`ADDON_Create`/`ADDON_GetTypeVersion`/`ADDON_GetTypeMinVersion` 三入口，
实际调用 `ADDON_GetTypeVersion(103)`/`MinVersion` 断言 audio encoder 实例
API `3.0.0`/`3.0.0`（xbmc 21.3-Omega SDK `kodi/versions.h` 口径，宏值已经
raw.githubusercontent 权威源、仓内 kodi-inputstream-rtmp 内嵌 dev-kit、
本包实际下载的 SDK tarball 三方核实一致）。headless 无 Kodi 宿主，编码主
循环依赖宿主回调（VFS 流接口、AudioEncoderInfoTag），无法在无宿主环境
诚实执行实际编码（P013 收缩到契约层）。

## 验证结果

见 `test_package/MANIFEST.yml` 与 run 报告（权威 CI
`ci/conan/build_and_test.sh`，profile `ci/conan/profiles/ohos-aarch64`）。
