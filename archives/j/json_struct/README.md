# json_struct

单头文件 C++20 JSON 序列化/反序列化库（MIT），将 JSON 直接解析到 C++ struct，
或将 C++ struct 序列化为 JSON。上游：https://github.com/jorgen/json_struct

## 特性

- 单头文件 `include/json_struct/json_struct.h`（实际为 include/json_struct/ 头集合）
- 支持 int64/uint64 全 64 位精度（arm64 场景关键）
- 中文 UTF-8 与 emoji round-trip 安全
- 枚举、嵌套结构、多态映射、别名、元数据反射
- 错误路径报告（行列 + 原因字符串）

## 适配说明（HarmonyOS PC）

- header-only INTERFACE 库，无编译产物；Conan `package_type = header-library`
- 上游测试使用 vendored Catch2 v2.13.1（无外部依赖），全量通过率 172/172 = 100%
- 消费者测试 `test_package/test_package.cpp` 覆盖鸿蒙中文场景与 64 位整型精度

## 构建

```bash
conan create archives/j/json_struct/1.0.2 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

版本列表见 `manifest.yaml`。