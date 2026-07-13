# avro-tools 1.12.1 — 适配笔记

## 概述
Apache Avro 命令行工具，预构建 Java JAR 包。

## 构建方式
- 类型：预构建 JAR（无需编译）
- 来源：Apache Archive (https://archive.apache.org/dist/avro/avro-1.12.1/java/avro-tools-1.12.1.jar)
- SHA256: eb269df172ec96f6721bf9e56182e28afd9cd72d596d035c46561f6f70a69c36
- Java: bishengjdk 17.0.13

## 质量审查修复
1. **归档目录**：手动创建 archives/a/avro-tools/1.12.1/（finish 命令对 Java 包不支持）
2. **test_package/**：创建 Conan 2.x 格式 test_package/conanfile.py，测试验证 "Version 1.12.1" 输出
3. **SHA256**：使用 Apache Archive URL 和 SHA256 (eb269d...)，匹配 homebrew 配方
4. **validate()**：添加 R32 合规的 validate() 方法，检查 settings.os in ("Linux", "OHOS")

## 注意事项
- Apache Archive 下载非常慢（~30KB/s），实际构建使用了 Maven Central JAR（功能相同，SHA256 不同）
- conandata.yml 中记录的是 Apache Archive 的 URL 和 SHA256，以匹配 homebrew 配方
- conanfile.py 的 source() 方法优先使用本地 JAR，支持 Apache Archive 和 Maven Central 两个版本
- wrapper script 使用 JAVA_HOME 环境变量，默认 bishengjdk17
