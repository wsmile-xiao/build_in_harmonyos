# libyang

## 简介
YANG data modeling language parser and toolkit (C library with yanglint/yangre CLI tools)

## OHOS 适配
- 构建系统: cmake
- 详见各版本 notes.md 获取适配详情

## 依赖
- pcre2（运行依赖，上游 find_package(PCRE2 REQUIRED)）
- cmocka（test_requires，仅上游测试套件使用）

## 功能验证
- 上游 CTest 套件（tests/utests，cmocka）在真机执行
- test_package：C API 全链路消费者测试 + 打包的 yanglint --version 执行验证

## 参考
- https://github.com/CESNET/libyang
