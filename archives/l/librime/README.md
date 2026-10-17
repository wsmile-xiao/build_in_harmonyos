# librime (Rime Input Method Engine)

## 简介

librime 是 Rime 输入法核心引擎（C++ 库），是 RIME 输入方案（拼音、仓颉、五笔、
注音等）的调度与执行核心，提供 schema 调度、词典/编码查询、用户词典（LevelDB）、
简繁转换（OpenCC）与配置解析（yaml-cpp）。

上游仓库: https://github.com/rime/librime · 主页: https://rime.im
License: BSD-3-Clause

## 功能特性

- 输入方案（schema）调度与切换（Rime engine / session）
- 词典与编码索引（marisa-trie）+ 用户词典持久化（LevelDB）
- 简繁/异体转换（OpenCC）
- YAML/Schema 配置解析与编译（yaml-cpp）
- 日志（google-glog）与 Boost 正则（regex）
- 附命令行工具：rime_deployer / rime_dict_manager / rime_patch / rime_table_decompiler

## OHOS 适配要点

- 必须共享构建（`BUILD_SHARED_LIBS=ON`）：上游根 CMakeLists 仅在共享构建下
  `add_subdirectory(tools)` 与 `add_subdirectory(test)`，否则无法构建/运行上游测试。
- 需设 `LINUX=ON`：OHOS 下 CMake 不定义 `LINUX`，librime 会走非 Unix Boost 分支
  而不链接 `boost_regex`；设置后走 Unix/Boost-regex 代码路径。
- 依赖定位：librime 用自定义 `Find*.cmake` 模块（`find_path`/`find_library`），
  需把各依赖的 `include/`、`lib/` 目录注入 `CMAKE_INCLUDE_PATH`/`CMAKE_LIBRARY_PATH`。
- 依赖（均为本仓已适配包）：boost/1.84.0、glog/0.7.1、yaml-cpp/0.8.0、
  leveldb/1.23、marisa/0.3.1、opencc/1.1.9、gtest/1.17.0（仅测试）。

## 依赖关系

编译/运行依赖：
- boost（regex）
- glog
- yaml-cpp
- leveldb
- marisa-trie（marisa）
- opencc
测试依赖：gtest

## 参考资料

- 官网: https://rime.im
- 源码: https://github.com/rime/librime
- 版本: 1.17.0（2026-06-05）
