# cute_png - Single-file PNG image loader/saver header

## 简介
cute_png 是 Randy Gaul 的 cute_headers 单头文件库集合中的一员，
提供一个 C 头文件 `cute_png.h`，实现 PNG 图像的加载、保存与图集
(texture atlas) 编译，内部包含 DEFLATE 兼容解压器与 LZ77 压缩器。
核心压缩/解压逻辑源自 Richard Mitton 的 tigr (Tiny Graphics) 库。

## 特性
- 单文件头库，零外部依赖，纯 C/C++（同时支持 C 与 C++）
- `cp_load_png` / `cp_load_png_mem` 从磁盘或内存加载 PNG
- `cp_save_png` / `cp_save_png_mem` / `cp_save_png_to_file` 保存 PNG
- 调色板 (indexed/paletted) PNG 加载与去调色板
- 纹理图集编译 `cp_make_atlas` / `cp_default_save_atlas`
- DEFLATE 兼容解压 + LZ77 压缩（v1.06 起）
- 定义 `CUTE_PNG_IMPLEMENTATION` 后在一个编译单元中包含即可生成实现

## OHOS 适配状态
- bootstrap 阶段（版本 1.0.0）：官方仓库/版本锚定与源码校验值已核验，
  最小归档与配方骨架已建立；尚未进入 adapt 与编译验证。
- 版本 1.0.0 对应上游 tinydeflate.h 内部版本 v1.0（12/23/2016 initial
  release，实现宏 TINYDEFLATE_IMPL、API 前缀 td*）；改名后的 master
  版本使用宏 CUTE_PNG_IMPLEMENTATION、API 前缀 cp_*。

## 来源
- 官方仓库: https://github.com/RandyGaul/cute_headers
- 1.0.0 锚定提交: 35fb638f58db（tinydeflate.h 内部版本 v1.0，2016-12-23
  initial release）
- 源码校验值 (tinydeflate.h @ 35fb638f58db):
  sha256 9218e5ed50ff8e5ddd0a4a520cb880e8653adc73efc7de6d434b1a92fe111c15

## 参考
- 官方仓库: https://github.com/RandyGaul/cute_headers
- 官方示例: examples_cute_png/
