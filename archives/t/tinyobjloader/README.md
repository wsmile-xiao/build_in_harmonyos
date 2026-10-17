# tinyobjloader

Tiny but powerful single file wavefront obj loader written in C++03.
No dependency except for C++ STL. It can parse over 10M polygons with moderate
memory and time.

- 上游: https://github.com/tinyobjloader/tinyobjloader
- 版本: 2.0.0rc13
- 类型: header-only（单文件 `tiny_obj_loader.h`，通过 `TINYOBJLOADER_IMPLEMENTATION` 宏在单一翻译单元内嵌实现）

## OHOS 适配要点

- header-only 库，Conan 配方仅安装头文件到 `include/`，不产生库文件。
- 消费者测试必须在单一翻译单元定义 `TINYOBJLOADER_IMPLEMENTATION`。
- 无第三方依赖，仅 C++ STL，无需额外工具链选项。
