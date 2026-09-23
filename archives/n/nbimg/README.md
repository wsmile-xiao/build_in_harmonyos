# nbimg

> 智能手机启动画面（Boot Splash）转换工具，支持 Android 与 WinCE 平台在 NB/IMG 与 BMP 格式之间互转。

## 简介

nbimg（Smartphone boot splash screen converter）是适用于 Android 和 WinCE 智能手机的启动画面转换器，作者 Pau Oliva（pof @ xda-developers）。它基于 HTC Splash Image（NB）格式，可在 NB/IMG 与标准 Windows BMP 图片之间互转，并提供 HTC NBH 打包（Model ID / SignMaxChunkSize / type 参数）与旧 WinCE "smartphone" 签名格式支持。

软件为单文件 C 程序（nbimg.c），上游为纯 GNU Make 工程，无任何外部依赖，编译与适配非常简单。

## OHOS 适配要点

- 上游 `make all` 目标同时会触发 `win32` 交叉构建（调用 `i586-mingw32msvc-gcc`），该工具链在 OHOS 构建沙箱中不存在。配方通过 `make ... nbimg` 仅构建原生目标，未改动上游源码，无补丁。
- 程序为标准 C + 标准库（stdio/stdlib/string/unistd/getopt），POSIX 接口（`getopt`/`unlink`）在 OHOS 工具链下可直接使用，无需平台宏。
- `convertBMP2NB` 的 padding 逻辑与 HTC splsh 签名是全局定义的常量行为，无平台差异；QVGA/VGA/HD 等常见分辨率均已内置自动识别。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| 无 | - | 纯标准库，无第三方依赖 |

## 功能验证

```bash
# BMP -> NB（QVGA 320x240，自动补齐 padding 与 HTC 签名）
nbimg -F splash.bmp

# NB -> BMP（自动识别分辨率，常见尺寸无需 -w/-h）
nbimg -F splash.nb

# 生成 HTC NBH（需 Model ID）
nbimg -F splash.bmp -D <model_id> -S 64 -T 0x600
```

## 参考

- [官方文档](https://github.com/poliva/nbimg)
- [源码仓库](https://github.com/poliva/nbimg)