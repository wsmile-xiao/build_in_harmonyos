# FASTBuild

FASTBuild is a high performance build system for Windows, OSX and Linux, supporting distributed compilation and object caching. It is used by many game developers, from small independent teams to some of the largest studios in the world.

## OHOS 适配要点

- 原项目使用自身 `.bff` 构建系统配置，无标准 configure/CMakeLists.txt
- 为 OpenHarmony/ARM64/musl 平台创建了完整的 CMakeLists.txt
- 移除 x86_64 特定编译参数（`-m64`），保留 `-fno-rtti`、`-fno-exceptions`
- 内嵌第三方库（LZ4 1.10.0、xxHash 0.8.2、Zstd 1.5.7）作为静态库编译
- 定义 `__LINUX__` 和 `RELEASE` 宏用于平台检测

## 依赖

无外部依赖，所有依赖库内嵌于源码。

## 许可证

Zlib License
