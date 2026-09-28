# leakcanary-shark

Shark 是 LeakCanary 项目中的 Java 堆转储（HPROF）解析与内存泄漏分析库族，纯 JVM Kotlin 实现。本归档包含四个模块：

- **shark** — 堆泄漏分析入口（`HeapAnalyzer`）、引用匹配、泄漏轨迹渲染
- **shark-graph** — 堆图抽象（`HprofHeapGraph`）、对象/类/实例遍历、保留字节计算
- **shark-hprof** — HPROF 文件读写（`Hprof`/`HprofReader`/`HprofWriter`）、Proguard 映射解析
- **shark-log** — `SharkLog` 统一日志

## 功能概述

- 解析 Android/OpenJDK 格式的 HPROF 堆转储
- 从 GC root 出发查找泄漏对象并计算最短引用路径与保留字节
- Proguard 混淆映射去混淆
- HPROF 记录级写出与裁剪/去混淆工具

## OHOS 适配

- 纯 Kotlin/JVM 库，无 native 代码，产物为 4 个 JAR（含 kotlin-stdlib/okio 运行时依赖）
- 使用 Gradle 7.4.2（与上游 wrapper 同版本）+ BiSheng JDK 17 源码编译
- 上游构建图包含 Android 模块与 AGP/dokka/detekt 等，配方以最小 patch 只保留 4 个 JVM 模块及其 2 个测试辅助模块
- 设备 `/tmp` 只读：构建与测试 JVM 的 `java.io.tmpdir` 经 `JAVA_TOOL_OPTIONS` 指向 HMBS 可写临时目录
- Gradle 自带启动脚本依赖 bash/grep 等，在设备 toybox 环境损坏；通过 `java -cp lib/* org.gradle.launcher.GradleMain` 直启
- Kotlin 1.4.21 编译器在 JDK17 上需要 `--add-opens java.base/...=ALL-UNNAMED`（放于 `org.gradle.jvmargs`，BiSheng JDK 不接受经 `JAVA_TOOL_OPTIONS` 传入）

## 依赖关系

- 运行时：kotlin-stdlib 1.3.72、okio 2.2.2（由 Gradle 从 Maven Central 解析并打包进 `libexec/`）
- 构建：BiSheng JDK 17（缺失时经 cmd-pkgs `install-jdk.sh` 自动安装）、Gradle 7.4.2（缺失时经固定 SHA256 的发行包自动安装）
- 测试（上游）：junit 4.12、assertj-core 3.9.1、内部 shark-test/shark-hprof-test 模块

## 参考资料

- 上游仓库：https://github.com/square/leakcanary （tag v2.14）
- 文档：https://square.github.io/leakcanary/
