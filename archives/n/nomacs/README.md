# nomacs

## 简介
nomacs 是一个免费开源的图像查看器，支持 RAW、PSD、TIFF 等多种图像格式。

## OHOS 适配
- Qt6Svg 在 OHOS 上是 stub 实现，无实际 SVG 渲染功能
- 需使用 DkSvgRendererStub 替代 QSvgRenderer 避免 undefined vtable symbols
- 添加 configure wrapper 转换 ./configure 参数为 cmake -D 参数

## 依赖
- Qt5 (5.15.2)
- exiv2 (0.28+)
- cmake

## 参考
- https://nomacs.org
- https://github.com/nomacs/nomacs