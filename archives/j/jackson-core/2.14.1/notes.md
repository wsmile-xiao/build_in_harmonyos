# jackson-core 2.14.1 — 适配笔记

## 概述
Jackson Core 是 Jackson 项目的核心 JSON 解析库，提供低级别的流式 JSON 输入/输出功能。
本 PR 采用源码编译方式，使用 Maven 构建并运行上游 JUnit 测试。

## 构建方式
- 类型：源码编译（Maven）
- 来源：GitHub tarball (https://github.com/FasterXML/jackson-core/archive/refs/tags/jackson-core-2.14.1.tar.gz)
- SHA256: 40c612c55d67592da161ad9af6543d07a8d4678f56d997ff55c151dfe4437d81
- 构建工具：Maven (via mvnw wrapper)
- Java: bishengjdk 17.0.13
- 许可证: Apache-2.0

## 上游测试
- 测试框架：JUnit 5 (junit-jupiter 5.8.2) + JUnit Vintage (junit-vintage-engine 5.8.2)
- 测试文件数：223 个 .java 文件
- 测试方法数：104 个 @Test 方法
- 运行命令：./mvnw clean package -B（package 阶段含 test，运行上游测试并产出 JAR）
- 运行位置：build() 方法中（CI Worker）

### 测试目录结构
src/test/java/com/fasterxml/jackson/core/ 下包含：
- 8 个根级测试文件（BaseTest, JsonLocationTest, TestExceptions 等）
- 13 个子目录：async, base64, filter, format, fuzz, io, json, jsonptr, read, sym, testsupport, type, util, write

## test_package 测试
test_package 通过 Java API 调用验证 jackson-core 功能（在鸿蒙真机上运行）：
1. 编写 TestJacksonCore.java，使用 JsonFactory 和 JsonParser 解析 JSON 字符串
2. test.sh 使用 javac 编译测试程序，java 运行验证 API 调用
3. 9 个断言：JAR 存在性、编译、6 个 JSON 解析断言、PASS 输出

## 注意事项
- jackson-core 是纯 Java 库，需要 JVM 运行环境（bishengjdk 17）
- Maven wrapper (mvnw) 会自动下载指定版本的 Maven
- build() 中运行上游测试需要网络连接（Maven 下载依赖）
- JAR 存放在 libexec/ 目录，通过 cpp_info.libdirs 导出
- JAVA_HOME 优先取环境变量，其次检测常见 JDK 路径（bishengjdk17、openjdk-17 等），缺失时清晰报错
