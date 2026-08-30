# cute_aseprite - Single-file Aseprite file parser

## 简介
cute_aseprite 是 Randy Gaul 的 cute_headers 单头文件库集合中的一员，
提供一个 C 头文件 `cute_aseprite.h`，用于把 `.ase` / `.aseprite` 文件
解析成紧凑方便的结构体集合（帧、层、cel、标签、切片、调色板等）。

## 特性
- 单文件头库，零依赖（内含 DEFLATE 解压实现）
- 跨平台 C/C++，定义 `CUTE_ASEPRITE_IMPLEMENTATION` 后在一个编译单元中
  包含即可生成实现
- 从文件或内存加载，自动混合帧像素（normal blend mode）

## OHOS 适配状态
- bootstrap 阶段（版本 1.0.0）：官方仓库/版本锚定与源码校验值已核验，
  最小归档与配方骨架已建立；尚未进入 adapt 与编译验证。

## 来源
- 官方仓库: https://github.com/RandyGaul/cute_headers
- 1.0.0 锚定提交: 6400bca5cbd84ce9113081b053abdf80d250a3b8（头文件版本 v1.00）

## 许可证
Zlib OR Unlicense（上游 cute_headers 双许可）
