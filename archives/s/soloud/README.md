# soloud

## 简介
SoLoud 是面向游戏的免费、可移植、可扩展音频引擎。本归档为 version_1_0（2013 首个 tag，版本字段保持 tag 原文）的 headless 核心适配。

## OHOS 适配
- 上游 version_1_0 无任何构建系统（demos 直接驱动 SDL）→ 补丁注入 headless CMakeLists.txt
- 只编纯软件混音核心：core（引擎）+ sinewave + speech（Klatt TTS）+ wav（含自带 stb_vorbis）+ filter
- 排除 SDL 后端（sdl/）与全部 SDL demos——零外部依赖，无音频设备环境（CI）可完整构建验证
- headless 消费者形态：`Soloud::init()` + `Soloud::mix()` 直接拉取 PCM
- stb_vorbis.c 以 C 编译，其余 C++

## 依赖
- 无（headless：全部可选依赖关闭）

## 功能验证
```bash
conan create archives/s/soloud/version_1_0 -pr:h ~/.conan2/profiles/ohos-aarch64 -pr:b ~/.conan2/profiles/ohos-aarch64
```

## 参考
- 主页: http://soloud-audio.com
- 源码: https://github.com/jarikomppa/soloud
