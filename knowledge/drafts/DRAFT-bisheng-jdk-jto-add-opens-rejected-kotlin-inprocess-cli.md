# draft-bisheng-jdk-jto-add-opens-rejected-kotlin-inprocess-cli

## 症状

在 OHOS 设备（BiSheng JDK 17.0.13+6）上用 Gradle 7.4.2 + Kotlin 1.4.21 构建
JVM 项目，按常规方式给 JDK17 强封装"开豁免"时接连撞墙，两种表象：

```
# 表象一：把 --add-opens 放进 JAVA_TOOL_OPTIONS —— 所有 JVM 直接拒启
$ export JAVA_TOOL_OPTIONS='--add-opens java.base/java.lang=ALL-UNNAMED'
$ java -version
Picked up JAVA_TOOL_OPTIONS: --add-opens java.base/java.lang=ALL-UNNAMED
Unrecognized option: --add-opens
Error: Could not create the Java Virtual Machine.
Error: A fatal exception has occurred. Program will exit.

# 表象二：opens 只放启动命令行（launcher），Gradle 构建里 Kotlin 编译崩
> Task :shark-log:compileKotlin FAILED
e: java.lang.NoClassDefFoundError: Could not initialize class
   org.jetbrains.kotlin.com.intellij.pom.java.LanguageLevel
Caused by: java.lang.reflect.InaccessibleObjectException: Unable to make
  protected void java.util.ResourceBundle.setParent(java.util.ResourceBundle)
  accessible: module java.base does not "opens java.util" to unnamed module
  （线程栈出现 RMI TCP Connection —— Kotlin daemon 进程）
```

## 根因

三条独立的工具链语义，在"旧工具链 + 新 JDK"组合下叠加：

1. **BiSheng JDK 拒绝经 `JAVA_TOOL_OPTIONS` 注入 `--add-opens`**。
   `JAVA_TOOL_OPTIONS` 在 JVM 初始化最早期解析，BiSheng 构建把该路径上的
   `--add-opens` 判为不可识别选项直接拒启；同一 flag 放命令行则正常接受。
   即：**这条环境变量在 BiSheng JDK 上不能承载 `--add-opens`**。

2. **Gradle daemon fork 造成 opens 作用域错配**。设置了
   `org.gradle.jvmargs` 时，Gradle 会 fork single-use daemon 执行构建
   （日志明示 "a single-use Daemon process will be forked"）。命令行
   `--add-opens` 只进 launcher 进程；Kotlin 1.4.21 内嵌编译器（IntelliJ
   平台代码 `DynamicBundle` 静态初始化）在 daemon 里反射
   `ResourceBundle.setParent`，无 opens 即抛
   `InaccessibleObjectException` → `Internal compiler error`
   （`NoClassDefFoundError: LanguageLevel` 只是静态初始化失败的次生错误）。

3. **Kotlin ≤1.4 忽略 gradle.properties 形式的编译策略属性**。在
   gradle.properties 里写 `kotlin.compiler.execution.strategy=in-process`
   无效——实测编译期仍拉起 RMI Kotlin daemon（独立 JVM，不带任何
   opens），必崩。策略只能以系统属性形式放在 Gradle 启动命令行。

## 修复

三处组合（缺一不可，leakcanary-shark/2.14 实证）：

```properties
# ① gradle.properties：daemon JVM 的 opens（fork daemon 生效，
#    Kotlin 内嵌编译器在 daemon 里运行）
org.gradle.jvmargs=-Xmx2g -XX:+UseParallelGC -Dfile.encoding=UTF-8 \
  --add-opens java.base/java.lang=ALL-UNNAMED \
  --add-opens java.base/java.util=ALL-UNNAMED \
  --add-opens java.base/java.io=ALL-UNNAMED \
  --add-opens java.base/java.net=ALL-UNNAMED \
  --add-opens java.base/java.nio=ALL-UNNAMED \
  --add-opens java.base/java.lang.reflect=ALL-UNNAMED
```

```python
# ② + ③ conanfile.py：launcher 命令行同样一组 opens（保护 launcher 进程），
#    且命令行 -D 强制 in-process（Kotlin ≤1.4 只认系统属性形式）
gradle_cmd = [
    java, "--add-opens", "java.base/java.lang=ALL-UNNAMED",
    ...,  # 六个 opens 与 jvmargs 相同
    "-Dkotlin.compiler.execution.strategy=in-process",
    "-classpath", os.path.join(gradle_home, "lib", "*"),
    "org.gradle.launcher.GradleMain", "--no-daemon", ...
]
```

**最小退路**：只在 `org.gradle.jvmargs` 一处放 opens。权衡：依赖 Gradle 的
daemon fork 行为（jvmargs 非空时必然 fork），launcher 自身进程不受保护；
若构建方式变化不再 fork，opens 即丢失。

**不要做**：
- 把 `--add-opens` 塞进 `JAVA_TOOL_OPTIONS`——BiSheng JDK 直接拒启，整个
  构建环境全灭（比原问题更糟）；
- 只在 gradle.properties 写 `kotlin.compiler.execution.strategy=in-process`
  就当已生效——Kotlin ≤1.4 忽略它，Kotlin daemon 照样拉起并崩溃。

## 验证

自包含对照探针（新 shell 可跑）：

```bash
# ① 注入路径拒绝
JAVA_TOOL_OPTIONS='--add-opens java.base/java.lang=ALL-UNNAMED' \
  /storage/Users/currentUser/bishengjdk17/bin/java -version
# → Unrecognized option: --add-opens
#    Error: Could not create the Java Virtual Machine.

# ② 命令行接受（同一 flag）
/storage/Users/currentUser/bishengjdk17/bin/java \
  --add-opens java.base/java.lang=ALL-UNNAMED -version
# → openjdk version "17.0.13" 2024-10-15（BiSheng，正常启动）
```

Kotlin 策略属性失效的复现口径：gradle.properties 设
`kotlin.compiler.execution.strategy=in-process` 后执行 `compileKotlin`，
失败栈线程名含 `RMI TCP Connection`（Kotlin daemon 被拉起的标志）；改为
启动命令行 `-D` 后该栈消失、编译成功。

实证：leakcanary-shark 2.14 三处组合落地后，上游 4 模块 172 个 @Test 用例
真机全部通过，权威 CI 全绿（2026-09-26）。

## 适用范围

- 任何在 BiSheng JDK 17 上构建需要 `--add-opens` 的旧工具链 JVM 项目的
  场景：Kotlin ≤1.4 内嵌编译器是最常见触发者（IntelliJ 平台代码反射
  ResourceBundle），旧版字节码/静态分析工具同理；
- 所有 Gradle fork daemon 的构建（`org.gradle.jvmargs` 非空即 fork）——
  opens 的作用域必须与真正执行编译的 JVM 对齐；
- 与 `DRAFT-gradle-launcher-toybox-xargs-quote-strip` 姊妹配合：Gradle 直启
  `GradleMain` 的 java 命令行正是本条 opens 与 `-D` 策略的承载点。

## 关联

- E083：同属 BiSheng JDK 特性族（该条为 ELF 签名机制影响 JNI 加载；本条为
  JVM 选项注入路径的接受域），不同侧面；
- E184：Java 构建工具链缺失需手动安装（命令不存在）；本条是"工具在但选项
  进不去"，互补；
- P-ENV-001（环境变量与构建系统语义冲突）：JAVA_TOOL_OPTIONS 这一环境变量
  与 BiSheng JDK 的选项解析语义冲突，应改用构建系统原生机制（jvmargs/命令
  行）承载；
- P-BUILD-001（平台限制必须降级而非绕过）：识别作用域后布局 opens（daemon
  + launcher 双处），而非反复重试或全局放开强封装。
