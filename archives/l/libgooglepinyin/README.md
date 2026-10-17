# libgooglepinyin

libgooglepinyin 是从 Android AOSP Google 拼音输入法抽出的拼音解码引擎库，提供整句拼音输入的核心解码能力：拼音音节切分、词典模糊匹配、整句候选生成、用户词典与预测。

## 功能概述

- 拼音流解析与音节切分（全拼/简拼）
- 基于二进制系统词典的整句解码与候选排序
- 用户词典管理与联想预测（im_get_predicts）
- 构建期词典生成工具 dictbuilder（将 UTF-16 原始词典文本编译为二进制词典）

## 安装产物

- 共享库（默认）：`libgooglepinyin.so.0`（由 Conan `shared` 选项控制）
- 公共头文件：`include/googlepinyin/`（`pinyinime.h` 等 18 个）
- 系统词典：`lib/googlepinyin/data/dict_pinyin.dat`
- pkg-config 元数据：`googlepinyin.pc`
- Conan CMake 目标：`libgooglepinyin::libgooglepinyin`

## OpenHarmony 适配

上游 data/ 目录在构建期运行刚编译的 `dictbuilder` 工具生成二进制词典，交叉编译时无法执行目标架构二进制。配方先用构建机 CMake pass 构建 `dictbuilder` 生成 `dict_pinyin.dat`，再由补丁后的 `data/CMakeLists.txt` 以 prebuilt 路径安装该词典。同时将 `cmake_minimum_required` 提升到 3.5（CMake 4 兼容）、install DESTINATION 相对化（支持 staged 安装）、`ENABLE_STATIC` 改为 static/shared 互斥（使 Conan `shared` 选项生效）。

## 依赖关系

核心库无外部 Conan 依赖，仅链接系统 pthread。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 0.1.2 | built | 2026-09-17 |
