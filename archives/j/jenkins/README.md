# Jenkins

## 简介
Jenkins 是一个开源的自动化服务器，用于持续集成和持续部署（CI/CD）。它可以帮助开发者自动化构建、测试和部署软件项目。

## OHOS 适配
- Jenkins 是纯 Java 应用，以 .war 文件形式发布
- 无需传统编译流程，直接下载官方 LTS 版本的 jenkins.war 文件
- 运行需要 Java 11 或更高版本（推荐 Java 17）
- OHOS 上已安装 BiSheng OpenJDK 17.0.13，可直接运行
- 无平台相关限制，Java 跨平台特性确保兼容性

## 排除与替代
无排除项。Jenkins 所有功能在 OHOS 上均可正常使用。

## 依赖
- **运行依赖**: Java 11+ (BiSheng OpenJDK 17.0.13 已安装)
- **可选依赖**: Git, Maven, Gradle（根据项目需要）

## 功能验证
```bash
# 启动 Jenkins
java -jar jenkins.war --version

# 或完整启动（后台运行）
java -jar jenkins.war --httpPort=8080
```

## 参考
- 官网: https://www.jenkins.io/
- LTS 版本下载: https://www.jenkins.io/download/
- 文档: https://www.jenkins.io/doc/
- 源码: https://github.com/jenkinsci/jenkins