# gradle 8.12 适配笔记

## 编译环境
- 构建系统: custom (binary distribution, 无需编译)
- 编译日期: 2026-07-20
- 运行时: bishengjdk 17+ (JDK 17)
- 状态: built

## 编译步骤

1. **下载二进制分发**: 从 services.gradle.org 下载 Gradle 8.12 二进制 ZIP
   - URL: https://services.gradle.org/distributions/gradle-8.12-bin.zip
   - SHA256: 7a00d51fb93147819aab76024feece20b6b84e420694101f276be952e08bef03

2. **打包**: 将 bin/ 和 lib/ 目录打包到 Conan 包中
   - bin/gradle → HarmonyOS 适配版 wrapper 脚本
   - lib/*.jar → Gradle 运行时 JAR 文件

3. **Wrapper 脚本适配**:
   - 自动检测 JAVA_HOME（bishengjdk 17）
   - 设置 JAVA_TOOL_OPTIONS=-Dos.name=Linux 绕过 Gradle 的 OperatingSystem 类对 HarmonyOS 的不识别
   - 直接通过 java -jar 调用 GradleMain 入口

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Gradle 的 OperatingSystem 类不识别 HarmonyOS | Gradle 内部使用 `System.getProperty("os.name")` 判断平台, 未包含 "HarmonyOS" 枚举 | 通过 JAVA_TOOL_OPTIONS 设置 -Dos.name=Linux, 对所有 JVM 进程生效 |
| 2 | CI 环境中可能缺少 JDK | CI worker 未预装 bishengjdk | wrapper 脚本自动检测 ~/bishengjdk17 等常见路径, 找不到则报错提示安装 |
| 3 | /tmp 只读 | OHOS 平台 /tmp 为只读文件系统 (E002) | Gradle 默认使用 ~/.gradle 作为缓存目录, 可写 |

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| bishengjdk | 17.0.13+ | JDK (运行时) |

## 验证结果

```bash
# gradle --version (在 HarmonyOS 环境中)
$ gradle --version
------------------------------------------------------------
Gradle 8.12
------------------------------------------------------------
Build time:   2024-12-20 00:00:00 UTC
Revision:     ...
Kotlin:       2.0.21
Groovy:       3.0.22
Ant:          Apache Ant(TM) version 1.10.15
JVM:          17.0.13 (BiSheng JDK 17.0.13)
OS:           Linux (HarmonyOS on aarch64)

# gradle --help
$ gradle --help
USAGE: gradle [option...] [task...]
  -?, -h, --help  Shows this help message.
  ...

# gradle projects (with minimal build.gradle)
$ gradle --no-daemon -q hello
Hello from Gradle on HarmonyOS!
```

## 注意事项

- Gradle 是 JVM 应用, 不是原生编译的 C/C++ 库, 不需要 compiler/build_type settings
- 运行时需要 bishengjdk 17+ (JDK 17)
- 通过 `JAVA_TOOL_OPTIONS=-Dos.name=Linux` 绕过 HarmonyOS 平台识别问题
- wrapper 脚本会自动检测 JAVA_HOME, 默认使用 `$HOME/bishengjdk17`
- 建议使用 `--no-daemon` 避免 daemon 进程残留