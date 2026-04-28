# harfbuzz

## 简介
HarfBuzz 是一个文本塑形（text shaping）引擎，用于将 Unicode 文本转换为正确定位的字形序列，支持 OpenType、TrueType 等字体格式。

## OHOS 适配
- harfbuzz 与 freetype 存在循环依赖：需先编译不带 harfbuzz 支持的 freetype，再编译 harfbuzz，最后重新编译带 harfbuzz 支持的 freetype
- meson 构建支持较好，autotools 也可用
- 需要标准 autotools 补丁（config.guess/config.sub）识别 HarmonyOS 系统

## 依赖
- 编译依赖：freetype, glib（可选）
- 运行依赖：无

## 功能验证
```bash
# 验证库安装
ls -la $HOME/usr/local/lib/libharfbuzz*
```

## 参考
- 官网：https://harfbuzz.github.io/
- 源码：https://github.com/harfbuzz/harfbuzz
