# lwjson

Lightweight JSON parser and serializer library written in C，由 Tilen Majerle (MaJerle) 维护。
设计面向嵌入式/受限内存场景：解析器基于 token 数组（零动态分配），支持对象/数组/字符串/
数字/布尔/空值，附带流式解析器与序列化器。

## 版本历史

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.9.0 | built | 2026-10-04 |

## 描述

lwjson 提供：

- `lwjson_parse` / `lwjson_parse_ex`：整块 JSON 解析为 token 链表
- `lwjson_find` / `lwjson_find_ex`：点分路径查找
- 类型化取值宏：`lwjson_get_val_int` / `lwjson_get_val_real` / `lwjson_get_val_string`
- 流式解析器 `lwjson_stream_*`（逐字符回调）
- 序列化器 `lwjson_serializer_*`（输出 JSON 文本）
- 调试模块 `lwjson_debug`（解析事件日志输出）

## 依赖

- 无第三方运行时依赖（纯 C 标准库）

## 适配要点

- CMake 构建，产出静态库 `lwjson` 与 `lwjson_debug`，公开头文件 `lwjson/*.h`
- 上游无 install() 规则，补丁 `0001-cmake-install-rules.patch` 补充安装规则
- `lwjson_opt.h` 引用用户配置头 `lwjson_opts.h`，包内附带默认生成配置
- 非 CLI 库（无 commands.json）
