# aixlog 1.5.0 适配笔记

## 库简介

Header-only C++11 日志库，单头文件 `include/aixlog.hpp`，零依赖。
通过 Sink 机制支持多种输出（cout/cerr/syslog/Android 等）。

## 关键构建选项

| 选项 | 说明 |
|------|------|
| package_type | header-library（无需编译，只打包头文件） |
| BUILD_EXAMPLE | OFF（不构建 example） |

## 产物

- 头文件：include/aixlog.hpp

## 验证

- test_package：AixLog::Log::init<SinkCout> + LOG 宏记录 debug/info/warning/error 日志
- 依赖：无（header-only，零依赖）
- 上游无独立测试套件（仅 example），补充消费者测试
