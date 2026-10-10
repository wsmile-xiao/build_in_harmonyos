# UPSE

UPSE（Unix PlayStation Sound Emulator）是一个用于解析和播放 PlayStation Sound Format（PSF）文件的 C 语言模拟库，并提供 `upse123` 命令行播放器。

## 功能概述

- 解析 PSF 文件及其元数据。
- 模拟 PlayStation R3000、DMA、计时器和 SPU 音频路径。
- 支持混响、插值和自定义 PlayStation BIOS 配置。
- 提供 `libupse` C API 与 `upse123` 命令行程序。

## OHOS 适配

- 使用 Conan 配方直接调用 OHOS Clang 构建上游核心 C 源码，避开上游旧版 Autotools 对平台三元组和已缺失 Audacious 1.4 SDK 的错误探测。
- 保留上游完整 `libupse` API 和 `upse123` CLI；可选 Audacious 插件与可选 libao 后端不属于核心库接口。
- 使用已发布的静态 PIC zlib 依赖，使共享版 `libupse` 不引入系统 `libz.so` 冲突。
- 消费者测试覆盖公开 API、无效 PSF 输入、命令行版本输出以及 HarmonyOS AArch64 ELF 契约。

## 依赖关系

- 编译依赖：OHOS Clang、LLVM ar、Conan 2.x。
- 第三方依赖：`zlib/1.3.1.1`。
- 运行依赖：HarmonyOS C 运行库和系统数学库 `libm`。

## 参考资料

- 上游主页：https://www.nenolod.net/projects/upse/
- 上游源码仓库：https://github.com/kaniini/upse
- 固定源码提交：https://github.com/kaniini/upse/commit/b71b54f315f6f7218c033405d475a2ae31a58dc8
