# FreeType

## 简介
FreeType 是一个免费的高质量字体渲染引擎，支持 TrueType、OpenType、CFF、Type 1 等多种字体格式。被广泛用于图形库、浏览器和操作系统中的字体渲染。

## OHOS 适配
- **循环依赖**: freetype 可选依赖 harfbuzz，但 harfbuzz 又依赖 freetype
  - 解决方案：先编译不带 harfbuzz 的 freetype，再编译 harfbuzz
- 使用 autotools 构建系统

## 依赖
- zlib（推荐）
- libpng（推荐）
- harfbuzz（可选，存在循环依赖）
- 编译工具: clang, make

## 功能验证
```bash
# 检查库文件
ls -la $HOME/usr/local/lib/libfreetype*
freetype-config --version
```

## 参考
- 官网: https://freetype.org/
- 源码: https://download.savannah.gnu.org/releases/freetype/
