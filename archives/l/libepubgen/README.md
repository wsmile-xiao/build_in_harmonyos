# libepubgen

libepubgen 是一个 C++ 库，用于生成 EPUB 格式电子书。它提供了三种生成器：

- **EPUBTextGenerator** — 文档类 EPUB 生成
- **EPUBPresentationGenerator** — 演示文稿类 EPUB 生成
- **EPUBDrawingGenerator** — 绘图类 EPUB 生成

支持 EPUB 2.0 和 EPUB 3.0 格式。基于 librevenge 文档模型抽象接口。

## 依赖

- librevenge-0.0（必选，提供输入流接口）
- Boost 头文件（必选，算法/字符串/UUID 等功能）

## 许可证

Mozilla Public License 2.0 (MPL-2.0)