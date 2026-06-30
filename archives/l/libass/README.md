# libass

libass 是一个用于渲染 ASS/SSA 字幕格式的库，主要用于视频播放器和字幕处理工具。

## 描述

libass 是一个轻量级的字幕渲染库，支持：
- ASS/SSA 字幕格式
- 高级样式特性（字体、颜色、位置、动画等）
-多种字体后端（fontconfig、CoreText、DirectWrite）
- HarfBuzz 文字整形引擎

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 0.17.0 | built | 2026-05-19 | 当前版本 |

## 编译依赖

- freetype2 >= 9.17.3
- fribidi >= 0.19.1
- harfbuzz >= 1.2.3
- fontconfig >= 2.10.92
- expat (fontconfig 依赖)

## 使用说明

```bash
# pkg-config 方式
pkg-config --cflags libass
pkg-config --libs libass

# 直接链接
-lass -lfreetype -lharfbuzz -lfribidi -lfontconfig
```

## 项目主页

- GitHub: https://github.com/libass/libass
- 官网: https://github.com/libass/libass