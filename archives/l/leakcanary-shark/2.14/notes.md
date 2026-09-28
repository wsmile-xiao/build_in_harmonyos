# leakcanary-shark 2.14 适配笔记

## 概述
leakcanary-shark（square/leakcanary 的 shark 子项目）是纯 JVM Kotlin 堆转储分析库族。本包以源码方式构建 shark / shark-graph / shark-hprof / shark-log 四个模块，运行上游全部 JUnit 测试，并打包模块 JAR 与运行时依赖。

- 上游仓库：https://github.com/square/leakcanary （tag v2.14，commit 8d29638ccf25e15d84b0119b6617f0069bc0b2d8）
- 许可证：Apache-2.0
- 源码：GitHub tarball，SHA256=b8a58752f8d0dd15207f8e4c4e44f654386b78c988e233120f8900caf30b1f05
- 构建系统：Gradle 7.4.2（与上游 gradle-wrapper.properties 同版本）
- JDK：BiSheng JDK 17.0.13（cmd-pkgs install-jdk.sh 自动安装）

## 构建方式
- 类型：源码编译（Gradle，非 wrapper 直启）
- 命令：`java -Dgradle.user.home=$SRC/.gradle-user-home -classpath $GRADLE_HOME/lib/* org.gradle.launcher.GradleMain --no-daemon --console=plain :shark-log:test :shark-hprof:test :shark-graph:test :shark:test :shark-log:jar :shark-hprof:jar :shark-graph:jar :shark:jar`（`GRADLE_USER_HOME` 环境变量同步钉在同一构建目录子目录，见环境要点 7）
- 产物：4 个模块 JAR（shark-2.14.jar 等）+ kotlin-stdlib-1.3.72.jar + okio-2.2.2.jar（+annotations-13.0.jar）

## 环境要点（真机踩坑记录）
1. **Gradle 启动脚本在设备上损坏**：toybox sh 下 bin/gradle 报 `Could not find or load main class "-Xmx64m"`。解法与 gradle 8.12 包一致：直接 `java -classpath lib/* org.gradle.launcher.GradleMain` 启动。
2. **HarmonyOS 平台识别**：Gradle OperatingSystem 类不识别 HarmonyOS → `JAVA_TOOL_OPTIONS` 追加 `-Dos.name=Linux`。
3. **/tmp 只读**：`JAVA_TOOL_OPTIONS` 追加 `-Djava.io.tmpdir=$TMPDIR`，Gradle/测试 JVM（JUnit TemporaryFolder、JvmTestHeapDumper 堆转储）全部落到 HMBS 可写临时目录。
4. **Kotlin 1.4.21 编译器在 JDK17 下崩溃**：`InaccessibleObjectException: ResourceBundle.setParent`（IntelliJ 平台代码反射）→ 需要 `--add-opens java.base/{java.lang,java.util,java.io,java.net,java.nio,java.lang.reflect}=ALL-UNNAMED`。注意：
   - BiSheng JDK **拒绝**经 `JAVA_TOOL_OPTIONS` 传入 `--add-opens`（`Unrecognized option: --add-opens`，JVM 直接无法启动）；
   - flags 放 `org.gradle.jvmargs`（fork 出的 single-use daemon 生效）+ 启动命令行双保险。
5. **Kotlin daemon 规避**：Kotlin 1.4.21 忽略 gradle.properties 里的 `kotlin.compiler.execution.strategy`，必须在启动命令行加 `-Dkotlin.compiler.execution.strategy=in-process`，否则仍拉起 Kotlin daemon（RMI）且无 add-opens 而崩溃。
6. **TYPESAFE_PROJECT_ACCESSORS**：根项目名必须匹配 `[a-zA-Z][A-Za-z0-9-_]*`，Conan 源码目录名不可控 → settings.gradle 里固定 `rootProject.name = 'leakcanary'`。
7. **打包不得依赖环境 Gradle 缓存（官方 PR CI #13017 L1 失败教训）**：
   - **症状**：开发设备 CI 全绿；官方 PR CI 上 G0/KC/JC/L0 全过、3 个 patch 应用成功、上游测试 172/172 全过，随后 `package()` 报 `Invalid configuration: Runtime dependency jar not found in the Gradle cache: kotlin-stdlib-1.3.72.jar (looked under ~/.gradle)` → L1 fail。
   - **根因**：旧配方 `package()` 用 `os.environ.get("GRADLE_USER_HOME") or ~/.gradle`（环境氛围缓存）找运行时 jar，而 `build()` 并不固定 Gradle JVM 的缓存位置——JVM 按 `gradle.user.home` 系统属性 > `GRADLE_USER_HOME` 环境变量 > `user.home/.gradle` 独立解析，`user.home` 还可被 `JAVA_TOOL_OPTIONS` 注入。两个路径只是"碰巧"一致；开发机 `~/.gradle` 热（开发期构建下载了全部依赖）掩盖了一切，属假阳性。冷 worker 上 JVM 把依赖下到它自己解析的缓存目录，与 `package()` 找的目录不一致；且 `~/.gradle` 可能缺失/部分播种/异 uid 不可列读（设备家目录 `drwxr-s--x`，异 uid 可穿越不可列目录，`os.walk` 静默返回空）→ 必挂。冷缓存复现实证：把 `~/.gradle` 移走并注入 `JAVA_TOOL_OPTIONS=-Duser.home=<空目录>`，Gradle 构建 exit 0、172/172 通过、依赖 jar 落在 `<空目录>/.gradle`，`package()` 在 `~/.gradle` 下找不到 → 报出与 PR CI 逐字相同的错误。
   - **最小修复**：`build()` 把 Gradle 用户主目录钉到构建目录内 `.gradle-user-home/`（env 变量 + 启动命令行 `-Dgradle.user.home` 双通道，后者在 JVM 参数序中覆盖 `JAVA_TOOL_OPTIONS` 的注入），`package()` 只从同一重算路径收集，不读环境变量、不回退 `~/.gradle`。全新 worker 无任何预热也必然成立。
   - **适用边界**：一切"build 期由 Gradle/Maven 下载依赖、package 期从工具缓存收集"的 JVM 配方；凡收集路径解析自环境（env var / user.home）皆须钉进构建目录并对环境零回退。依赖固定版本清单（kotlin-stdlib 1.3.72 / okio 2.2.2 / annotations 13.0）与上游 v2.14 version catalog（`kotlinLib=1.3.72`、`okio2=2.2.2`）核对一致。

## 补丁（3 个，均为最小改动）
1. `0001-minimal-jvm-settings-and-root-build.patch`：settings.gradle 只保留 4 个 shark 模块 + 2 个测试辅助模块（shark-test/shark-hprof-test）+ typesafe 预览；根 build.gradle 只保留 kotlin 插件 classpath、mavenCentral/gradlePluginPortal 仓库（移除已死的 jcenter()）、GROUP/VERSION_NAME、Kotlin apiVersion=1.3 与 FULL testLogging。移除的 AGP/dokka/detekt/binary-compatibility-validator/keeper/vanniktech-publish/installGitHooks/siteDokka 均为 Android 发布/文档/静态检查基础设施，与 JVM 模块构建测试无关。
2. `0002-jvm-modules-drop-maven-publish-plugin.patch`：4 个模块移除 `com.vanniktech.maven.publish`（仅用于发布 Maven Central，OHOS 打包不需要，也避免引入 dokka javadoc 链）。
3. `0003-gradle-properties-jdk17-tuning.patch`：`org.gradle.jvmargs` 提升 -Xmx2g 并追加 --add-opens。

## 上游测试
- 框架：JUnit 4.12（org.junit.Test），Gradle test 任务
- 静态统计：29 个测试文件 / 172 个 @Test 方法
  - shark：14 个套件 / 120
  - shark-graph：9 个套件 / 46
  - shark-hprof：2 个套件 / 3
  - shark-log：1 个套件 / 3
- 实际执行（真机 bishengjdk17，2026-09-26）：**executed=172, passed=172, failed=0, errors=0, skipped=0**，从各模块 `build/test-results/test/TEST-*.xml` 汇总，与静态 @Test 数完全一致（无 skip/disable/exclude）。
- 测试中 JvmTestHeapDumper 经 HotSpotDiagnosticMXBean 真实转储测试 JVM 堆，堆解析测试在设备上完整走通。

## test_package
- `test.sh` 编译并运行 `TestShark.java`（9 项断言）：
  1. HprofWriter 生成合法 HPROF（GC root + 类/实例转储）
  2. HeapAnalyzer.analyze() 泄漏分析成功（computeRetainedHeapSize=true）
  3. applicationLeaks=1 且 LeakTrace 渲染含泄漏类名
  4. HprofHeapGraph 类查找（A/B）+ gcRoots 数量
  5. ProguardMappingReader 类/字段去混淆
  6. SharkLog 日志捕获
- 真机运行 9/9 通过，输出 HMBS_TEST_PACKAGE_RESULT。

## 打包结构
- `libexec/shark-2.14.jar`、`shark-graph-2.14.jar`、`shark-hprof-2.14.jar`、`shark-log-2.14.jar`
- `libexec/kotlin-stdlib-1.3.72.jar`、`okio-2.2.2.jar`、`annotations-13.0.jar`（运行时依赖）
- `licenses/LICENSE.txt`

## 注意事项
- 纯 JVM 库，无 native 代码，无 ELF 产物；settings 四项齐全满足 L0p 门禁
- 依赖 kotlin-stdlib/okio 由 Gradle 在构建期从 Maven Central 公网解析（vinnie/jackson-core 先例），打包时从构建目录内封闭的 Gradle 缓存（`.gradle-user-home/`，`build()` 钉入）精确收集固定版本，对环境 `~/.gradle` 零依赖（见环境要点 7）
- 首次 CI 运行需下载 Gradle 发行包（腾讯镜像优先，SHA256 固定）与 Maven 依赖，耗时约 5-10 分钟；封闭缓存使每次冷运行都重新解析 Maven 依赖，属确定性行为
