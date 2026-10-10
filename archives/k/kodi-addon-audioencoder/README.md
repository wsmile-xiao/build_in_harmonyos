# kodi-addon-audioencoder

Kodi 音频编码器插件 "Wav Audio Encoder"（上游项目 id `audioencoder.wav`，
xbmc/audioencoder.wav）的 OHOS 移植。Kodi 21 "Omega" 系二进制音频编码器
插件：C++ 实现，在 Kodi 内部以模块（`audioencoder.wav.so`）形式被宿主
加载，无独立运行入口。

## 版本

| 版本 | 上游 tag | 状态 | 说明 |
|---|---|---|---|
| 21.0.2 | 21.0.2-Omega | built | 零外部编解码库（PCM 经宿主 VFS 直写），Kodi SDK 头取自 xbmc 21.3-Omega |

## 家族映射

"kodi-addon-audioencoder" 对应 xbmc org 的 audioencoder 家族四仓
（wav / vorbis / lame / flac，官方 tag 均 `21.0.2-Omega`）。本包取
**audioencoder.wav**：单翻译单元、上游 DEPLIBS 为空、零外部依赖，为
同版本 tag 候选中依赖最简者（vorbis/lame/flac 均需外部编解码库）。

## OHOS 适配要点

1. 上游 CMake 需要 `find_package(Kodi)` + `build_addon()`（kodi-addon-dev
   发行内容，registry 无 kodi 包）。配方自带 `recipe-cmake/` 构建入口，按
   上游语义构建**上游原样源码**：模块目标 `audioencoder.wav`（PREFIX 空，
   产物名 `audioencoder.wav.so`），无 GL/EGL 相关设置。
2. Kodi 插件 SDK 头（`kodi/`）从 xbmc 21.3-Omega 发布 tarball 的
   `xbmc/addons/kodi-dev-kit/include` 子树选择性提取（conandata
   `sources.sdk`，双 URL + sha256 固定）。
3. **不定义** `BUILD_KODI_ADDON`/`ADDON_*_USED`（DRAFT-KODI01 禁令），
   test_package 运行时断言 `ADDON_GetTypeVersion(103)=="3.0.0"`。
4. 上游无测试套件（见 `21.0.2/notes.md` 的证据记录）；test_package 做真实
   消费者检查：dlopen 打包模块 + dlsym 三个 Kodi 二进制插件入口符号 +
   运行 `ADDON_GetTypeVersion/MinVersion` 校验 audio encoder 实例 API
   版本。

## 已知限制

- 无宿主环境下无法验证实际编码（编码主循环依赖 Kodi 宿主的 VFS 流回调）；
  Kodi 宿主移植属后续任务，本包提供可加载的模块产物。
