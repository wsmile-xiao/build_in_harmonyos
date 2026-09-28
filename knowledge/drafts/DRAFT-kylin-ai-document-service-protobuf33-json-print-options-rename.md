# DRAFT: protobuf 33.x 的 JsonPrintOptions 字段改名（OHOS 适配实战）

## 基本信息
- **状态**: draft（不预占正式 E 编号）
- **严重度**: 2
- **类别**: protobuf, api-rename, portability, ohos, source-patch
- **来源**: kylin-ai-document-service 1.2.0.0 HarmonyOS PC 适配（W3 构建）

## 错误特征

```
/storage/Users/.../src/client.cpp:59:13: error: no member named
    'always_print_primitive_fields' in 'google::protobuf::json::PrintOptions'
    options.always_print_primitive_fields = true;
    ~~~~~~~ ^
1 warning and 1 error generated.
```

## 根因分析

1. 上游 `src/client.cpp` 用 protobuf 的 JSON 工具把请求/响应消息序列化为 JSON：
   ```cpp
   google::protobuf::util::JsonPrintOptions options;
   options.add_whitespace = true;
   options.always_print_primitive_fields = true;
   ```
2. protobuf 33.x 的头文件布局已经迁移：`google/protobuf/util/json_util.h` 现在只是别名转发
   ```cpp
   using JsonPrintOptions = ::google::protobuf::json::PrintOptions;
   ```
   而真正的 `struct PrintOptions` 定义在 `google/protobuf/json/json.h`，字段集合为：
   `allow_legacy_nonconformant_behavior` / `add_whitespace` /
   **`always_print_fields_with_no_presence`** / `always_print_enums_as_ints` /
   `preserve_proto_field_names` / `unquote_int64_if_possible`。
   旧名 `always_print_primitive_fields` 已彻底移除（不是别名，是删名）。
3. 制品仓依赖组合无法回避该版本：`grpc/1.84.0` 精确约束 `protobuf/33.6`
   （尝试 `33.6.1` 会得到 `Version conflict … originates from grpc/1.84.0`），
   所以“换旧版 protobuf”不成立。

## 推荐方案

**方法**: portability-patch（字段名等价替换）

```diff
-    options.always_print_primitive_fields = true;
+    options.always_print_fields_with_no_presence = true;
```

- 语义一一对应：二者都表示“始终打印不具 presence 语义的字段”（隐式 presence 的零值、
  空列表/映射），仅命名随 proto3 JSON 规范收敛而更新。
- 保持为独立补丁（本例 `0003-protobuf33-print-options.patch`），不加平台宏（R8）、
  不条件编译。

## 禁止事项

| 禁止 | 原因 |
|---|---|
| 直接删除该赋值行 | 会静默改变对外 JSON 契约（空字段不再输出），下游解析行为变化 |
| 用 `#if PROTOBUF_VERSION >= ...` 双写新旧名 | 属平台/版本宏绕道；本项目规则要求补丁保持可移植直改（R8 精神），且此处无需兼容旧版本 |

## 经验法则

> 遇到 “no member named X in google::protobuf…” 时，先到
> `$PACKAGE/include/google/protobuf/json/json.h` 看 `struct PrintOptions` /
> `struct ParseOptions` 的真实字段列表，再决定“改名”还是“改语义”——
> protobuf 的 C++ JSON 与 text_format 选项在 30.x→33.x 有多轮重命名。

## 关键词

protobuf 33, JsonPrintOptions, PrintOptions, always_print_primitive_fields,
always_print_fields_with_no_presence, json_util.h, MessageToJsonString, API drift

---
*由 kylin-ai-document-service 1.2.0.0 适配沉淀（2026-09-26）*
