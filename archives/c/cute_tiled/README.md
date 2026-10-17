# cute_tiled

cute_tiled 是 RandyGaul/cute_headers 系列的单头文件 C 库，用于高效加载 Tiled
地图编辑器导出为 JSON 格式的地图文件（.tmj / .json）。

- 官方仓库: https://github.com/RandyGaul/cute_headers
- 头文件: `cute_tiled.h`（1.0.0 阶段为 `tinytiled.h`，2018-05-21 改名）
- 使用方式: 在单个翻译单元中 `#define CUTE_TILED_IMPLEMENTATION` 后 `#include` 该头文件

## 版本说明

cute_headers 仓库不提供按子库发布的独立 tag/release。cute_tiled 的版本标识
内嵌在头文件修订历史中：

- 1.00 (03/24/2018) initial release —— 对应本归档 1.0.0
- 官方引入 commit: `17014665d51e`（added tinytiled.h，头文件内部版本行 `tinytiled.h - v1.00`）

## OHOS 适配状态

- 当前阶段: bootstrap（最小归档/配方骨架）
- 未进入 adapt/编译/W3/finish/提交

## 归档结构

```
archives/c/cute_tiled/
  ├── manifest.yaml        # 软件级元数据 + 版本索引
  ├── README.md            # 本文件
  └── 1.0.0/
      ├── conanfile.py     # Conan 配方骨架
      ├── conandata.yml    # 源码 URL + sha256
      ├── manifest.yaml    # 版本级元数据
      ├── notes.md         # 适配笔记
      └── test_package/    # Conan 测试骨架
```
