# jackson-core

Jackson Core — Jackson 项目的核心 JSON 解析库，提供低级别的流式 JSON 输入/输出功能。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.14.1 | built | 源码编译（Maven），GitHub 下载 |

## 概述

jackson-core 是 FasterXML Jackson 项目的核心组件，提供：
- 流式 JSON 解析（JsonParser）
- 流式 JSON 生成（JsonGenerator）
- JsonFactory 工厂类

## 构建方式

- **类型**: 源码编译（Maven）
- **来源**: GitHub (FasterXML/jackson-core tag jackson-core-2.14.1)
- **Java 运行时**: bishengjdk 17.0.13
- **许可证**: Apache-2.0

## 测试

test_package 通过 Java API 调用验证 jackson-core 功能：
- 编写 TestJacksonCore.java，使用 JsonFactory/JsonParser 解析 JSON
- test.sh 使用 javac 编译、java 运行测试程序
- 6 个 JSON 解析断言覆盖 START_OBJECT、FIELD_NAME、VALUE_STRING、VALUE_NUMBER_INT、END_OBJECT
