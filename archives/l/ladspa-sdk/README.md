# ladspa-sdk

LADSPA (Linux Audio Developer's Simple Plugin API) SDK — the reference
implementation from ladspa.org, shipping the `ladspa.h` API header, five
example LADSPA plugins and three host tools.

## 描述

ladspa-sdk 包含 LADSPA 插件 API 的官方 SDK：

- **`ladspa.h`** — 核心 API 头文件，定义 `LADSPA_Descriptor` 结构体及
  `ladspa_descriptor()` 入口点，是音频插件与 host 之间的 ABI 契约。
- **5 个示例插件**（amp / delay / filter / noise / sine）— 参考实现，供
  host 程序通过 `dlopen()` 加载。
- **3 个 host 工具**（`analyseplugin` / `applyplugin` / `listplugins`）—
  用于列出、分析与应用 LADSPA 插件。

LADSPA 是一个轻量级的音频插件标准，为音频处理应用提供统一的插件接口。

## 已编译版本

- 1.17 (2026-08-25) — OpenHarmony / HarmonyOS PC aarch64

## 依赖

- libsndfile/1.2.2（仅 host 工具需要，用于 wave 文件读写）
- 系统库 libdl、libm（OHOS 自带）
- 插件与头文件本身无外部依赖

## 特性

- 提供 `ladspa.h` 头文件（header-only API）
- 提供 5 个示例插件 `.so`（`lib/ladspa/`）
- 提供 `analyseplugin` / `applyplugin` / `listplugins` 命令行工具（`bin/`）

## 使用方法

```bash
# 列出可用插件（搜索 LADSPA_PATH）
listplugins

# 分析插件端口与参数
analyseplugin /path/to/amp.so

# 应用插件处理音频
applyplugin input.wav output.wav plugin.so:label:param1:param2
```

作为库消费（编写 host 或插件）：

```cmake
find_package(ladspa-sdk CONFIG REQUIRED)
target_link_libraries(my_host PRIVATE ladspa-sdk::ladspa-sdk)
```

host 通过 `dlopen()` 加载插件并 `dlsym(,"ladspa_descriptor")` 获取描述符函数。

## 上游

- 主页: https://www.ladspa.org/
- 源码: https://www.ladspa.org/download/ladspa_sdk_1.17.tgz
- 许可证: LGPL-2.1-or-later
