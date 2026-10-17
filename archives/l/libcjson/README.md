# libcjson

libcjson（上游项目 cJSON）是一个 ANSI C 语言实现的超轻量级 JSON 解析器，单文件实现、零外部依赖。

## 功能概述

- 解析和构建 JSON 数据
- 单文件实现，零外部依赖
- 支持 JSON 的所有标准类型
- 可选择启用打印格式化

## OHOS 适配

- 构建系统为 cmake，需要 1 个补丁（CMakeLists.txt 适配：cmake_minimum_required 3.0→3.5、c89→c99）
- 上游测试 22/22 通过（含 cJSON_test 自测与 utils 测试）

## 依赖关系

- ANSI C 编译器（零外部依赖）

## 参考资料

- 源码: https://github.com/DaveGamble/cJSON
