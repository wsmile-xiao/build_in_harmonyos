# openfst

OpenFst 是一个用于构造、组合、优化和搜索加权有限状态转换器（FST）的开源库。有限状态转换器在语音识别、自然语言处理、机器翻译、计算生物学等领域有广泛应用。

## 主要功能

- **FST 操作**: 支持 compose、concatenate、union、intersection 等基本操作
- **FST 优化**: 支持 determinize、minimize、push、prune 等优化操作
- **FST 算法**: 支持 shortest-path、top-sort、arc-sort、connect 等算法
- **多种弧类型**: 标准（tropical）、log、lexicographic、power 等权重语义
- **脚本接口**: 提供 Python 风格的脚本命令行工具（fstcompile、fstinfo、fstdraw 等）

## 编译产物

- 37 个命令行工具（bin/）
- libfst.so — 核心 FST 库
- libfstscript.so — FST 脚本封装库
- 107 个头文件（include/fst/）

## 鸿蒙平台适配

openfst 在鸿蒙（OpenHarmony）平台上需要以下补丁：
1. config.guess — 添加 aarch64-ohos 平台识别
2. config.sub — 添加 ohos 操作系统支持
3. configure — 修复 shell 引号兼容性问题

## 可用版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.8.4 | published | 2026-05-27 |