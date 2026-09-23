# DRAFT: 上游目录级编译宏不随安装导出导致消费者宏默认值漂移

*来源 PR: !9046（flatbuffers/25.12.19）· 2026-09-09*

## 错误特征

```
undefined symbol: flatbuffers::ClassicLocale::instance_
TEST FAILED: parser_test.cpp:483 invalid number: "0x12.34p-1"
```

## 根因分析

上游 CMakeLists.txt 以目录级 `add_definitions(-DFLATBUFFERS_LOCALE_INDEPENDENT=$<BOOL:...>)`
注入探测得到的编译宏。目录级定义**不随 `cmake install` 导出**，于是：

- 库内目标按探测值编译（本工具链探测失败 → 0）；
- 消费者头文件在 OHOS（`_XOPEN_VERSION >= 700`）经 base.h `#ifndef` 默认分支取 1，
  引用仅在宏>0 时编译进库的静态数据成员 `ClassicLocale::instance_` → 链接失败。

平台缺陷（决定修复方向）：OHOS libc 的 `strtod_l` 在传入 flatbuffers ClassicLocale
创建的 locale_t 对象时，hex-float 字面量在 "0x" 处停止解析（返回 0）；同一字符串用
裸 `strtod` 或 `newlocale(LC_ALL_MASK,"C",0)` 新建对象均正常解析 9.1015625。即
=1 路径在 OHOS 上语义不可用。

## 推荐方案

1. 配方 `generate()`：`tc.variables["FLATBUFFERS_LOCALE_INDEPENDENT"] = "OFF"`（与上游
   探测在同工具链的落点一致）。
2. `package_info()`：`cpp_info.defines = ["FLATBUFFERS_LOCALE_INDEPENDENT=0"]` 导出，
   库与消费者强制同路径。
3. 审计点（跨仓库通用）：头文件 `#ifndef X` 平台默认 + 源文件 `#if X>0` 条件编译符号 +
   CMake add_definitions 注入的组合，必须核查宏是否随安装导出、两侧取值是否一致。

## 验证

微观探针：同 util.cpp 按 =0/=1 双编译 × ClassicLocale/新 locale/裸 strtod 三对照。
最终：上游测试 105/105（直接调用层）、消费者 1/1、CI 绿（PR !9046）。

## 反例与边界

- 消费者自行覆盖宏为 1：OHOS 上触发 hex-float 解析差异（行为差异，非链接错误）。
- glibc/MSVC 的 =1 路径不受影响；musl 无本地化语义，=0 无功能损失。
