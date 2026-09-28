# Clay

Clay（C Layout）是一个高性能 2D UI 布局库（nicbarker/clay，Zlib）。整个库是一个 ~4.4k LOC 的 clay.h 单头文件，零依赖（连 C 标准库都不需要）。采用类 Flexbox 的布局模型，支持文本换行、滚动容器、宽高比缩放；React 风格的嵌套声明式语法；渲染器无关——输出排序后的渲染图元列表，可对接任何渲染引擎（raylib/SDL2/SDL3/Sokol/cairo/terminal/win32 GDI/web wasm 等官方 renderers 目录提供参考实现）。

## 功能概述
- 微秒级布局性能；静态 arena 内存（无 malloc/free）
- Flexbox 式布局：FIT/GROW/FIXED/PERCENT 宽高、padding、childGap、对齐、TOP_TO_BOTTOM/LEFT_TO_RIGHT 方向
- 文本：MeasureText 回调机制（消费者提供字体度量）、换行模式（WORDS/NEWLINES/NONE）
- 滚动容器：clip 裁剪（SCISSOR_START/END 渲染命令）、子内容偏移
- 浮动元素、边框、圆角、自定义渲染命令
- 错误处理回调（Clay_ErrorHandler）
- C11 单头零依赖；wasm 15KB 可编译

## OHOS 适配
- 配方形态：clay_impl.c 承载 CLAY_IMPLEMENTATION → libclay.a 静态库，消费者 link clay::clay + include clay.h（声明模式）
- 上游无注册测试（N=0）：CI build matrix 3 项 + docker 构建冒烟 1 项均以设备 clang 交叉编译运行等价执行
- test_package：两个真实布局场景 8 项断言（flex 固定宽/文本回调/滚动裁剪 SCISSOR 对等契约）
- 纯计算布局库无平台 API，天然 headless 可测

## 依赖关系
- **编译依赖**: 无
- **运行依赖**: 无

## 参考资料
- 官网: https://github.com/nicbarker/clay
- 介绍视频: https://youtu.be/DYWTw19_8r4
