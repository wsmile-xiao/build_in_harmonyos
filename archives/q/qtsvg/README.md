# qtsvg

Qt SVG 模块，提供 SVG 文件的渲染和显示功能。

## 描述
qtsvg 是 Qt 框架的 SVG 支持模块，包含 QtSvg 和 QtSvgWidgets 两个库：
- QtSvg: 提供 QSvgRenderer 和 QSvgGenerator 类，用于 SVG 文件的渲染和生成
- QtSvgWidgets: 提供 QSvgWidget 类，用于在 Qt Widget 应用中显示 SVG 内容

## 已编译版本
- 6.11.1 (2026-05-20)

## 依赖
- qtbase 6.11.1

## 使用方法
```cmake
# CMake 中使用
find_package(Qt6Svg REQUIRED)
target_link_libraries(myapp Qt6::Svg Qt6::SvgWidgets)
```

```pkg-config
# pkg-config 使用
pkg-config --cflags --libs Qt6Svg
```