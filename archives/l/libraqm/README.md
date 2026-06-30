# libraqm

## 简介

libraqm 是一个用于复杂文本布局的库，使用 HarfBuzz 和 FreeType 实现高质量的文本渲染，支持多语言排版。

## OHOS 适配

- **依赖**: 需要 freetype2、harfbuzz、fribidi
- **meson 配置**: 使用 `--wrap-mode=nofallback` 防止子项目下载

## 依赖

- freetype2 >= 26.6.20
- harfbuzz >= 14.2.0
- fribidi >= 1.0.16

## 功能验证

```bash
pkg-config --modversion raqm
# 输出: 0.10.5
```

## 参考

- 官网: https://github.com/HOST-Oman/libraqm