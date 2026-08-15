# clinfo

> Print all known information about all available OpenCL platforms and devices

## 简介

clinfo 是一个简单的命令行工具，枚举系统中所有可用的 OpenCL 平台和设备，并打印其全部已知属性（平台名称、设备类型、扩展、版本等），常用于验证 OpenCL 环境是否正确配置。纯 C 实现，无图形界面依赖。

## OHOS 适配要点

- **构建系统**：纯 Makefile 项目（无 autotools/cmake/meson），直接 `make` 构建。
- **OpenCL 头文件**：OHOS 系统不提供 `CL/cl.h`，配方中 vendor 官方 KhronosGroup/OpenCL-Headers 归档（v2024.05.08），通过 `CPPFLAGS=-I<vendored>/OpenCL-Headers` 编译。
- **ELF 签名**：clinfo 可执行文件需用 `/data/service/hnp/bin/binary-sign-tool` 自签（`-selfSign 1`）才能在 HarmonyOS 上执行。
- **运行时**：链接系统 `libOpenCL`（ICD loader）。无 OpenCL 平台时输出 `Number of platforms: 0` 并正常退出（`CL_PLATFORM_NOT_FOUND_KHR` 被上游容错）。

## 依赖

- 编译期：vendored OpenCL-Headers（官方归档）
- 运行期：系统 libOpenCL（ICD loader）

## 功能验证

```bash
clinfo -l      # 简要列出平台与设备
clinfo --version
clinfo        # 完整打印平台/设备属性
```

## 参考

- [clinfo GitHub 仓库](https://github.com/Oblomov/clinfo)
- [OpenCL-Headers GitHub 仓库](https://github.com/KhronosGroup/OpenCL-Headers)
