# Alloy Analyzer

[Alloy](https://alloytools.org) 是一种用于描述结构并探索它们的建模语言。Alloy Analyzer
提供符号建模、SAT 求解、实例/反例查找能力，广泛用于软件建模、安全机制验证等领域。

本归档适配 **Alloy 6.2.0** 到 HarmonyOS PC（arm64）平台。Alloy 6 是自包含可执行程序，
包含 Kodkod 模型查找器与多种 SAT 求解器。采用**源码构建**方式：bnd/Gradle 工作区
`gradle build` 一次完成模块编译、上游 JUnit 测试（25/25 通过）与自包含 JAR 产出，
构建产物通过 HarmonyOS 适配版 wrapper 脚本调用本机 JDK 运行。

## 特性

- CLI 子命令：`version` / `exec`（执行 Alloy 程序并求解）/ `commands`（列出命令）/
  `solvers` / `natives` / `prefs` / `gui` / `lsp`（内嵌语言服务器）
- 支持经典与时间逻辑建模（temporal model-checking，可选依赖 NuSMV/nuXmv）
- 打包产物：`libexec/org.alloytools.alloy.dist-6.2.0.jar` + `bin/alloy` wrapper

## 使用

```bash
alloy version
alloy commands model.als
alloy exec model.als      # 求解并生成 receipt.json 与解决方案
```

## 平台限制

- 运行时需 JDK 17+（`JAVA_HOME` 或 `~/bishengjdk17`）
- Kodkod 原生 SAT 求解器无 aarch64-Linux 预编译库时自动回退纯 Java SAT4J 求解器
- 时间逻辑验证（Electrod 后端）需用户自行安装 NuSMV/nuXmv（可选）
