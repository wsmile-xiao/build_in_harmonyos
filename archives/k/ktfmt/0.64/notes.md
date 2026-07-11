# ktfmt 0.64 适配笔记

## 编译环境
- 构建系统: custom (Gradle shadowJar)
- 编译日期: 2026-07-03
- 运行时: bishengjdk 17.0.13 (JDK 17)
- 构建工具: gradle 9.6.1
- 状态: published (conan-verify 8 道门禁全通过)

## 编译步骤

1. **下载源码**: 从 GitHub 下载 ktfmt v0.64 源码包 (tar.gz)
   ```bash
   # 使用 gitcode 镜像加速 GitHub 下载
   curl -L -o ktfmt-0.64.tar.gz https://github.com/facebook/ktfmt/archive/refs/tags/v0.64.tar.gz
   ```

2. **配置 Maven 镜像**: 修改 `~/.gradle/init.gradle` 使用阿里云 Maven 镜像源
   ```gradle
   allprojects {
       repositories {
           maven { url 'https://maven.aliyun.com/repository/public' }
           maven { url 'https://maven.aliyun.com/repository/gradle-plugin' }
       }
   }
   ```

3. **构建 fat JAR**: 使用 Gradle shadowJar 任务打包所有依赖
   ```bash
   export JAVA_HOME="$HOME/bishengjdk17"
   export PATH="$JAVA_HOME/bin:$HOME/usr/local/bin:$PATH"
   export GRADLE_OPTS="-Xmx512m -Dorg.gradle.jvmargs=-Xmx512m"
   gradle shadowJar --no-daemon -Dorg.gradle.daemon=false
   ```
   产物: `core/build/libs/ktfmt-0.64-with-dependencies.jar` (~68MB)

4. **安装**: 将 JAR 和 wrapper 脚本安装到 Conan package
   - JAR → `libexec/ktfmt-0.64-with-dependencies.jar`
   - Wrapper → `bin/ktfmt` (调用 `java -jar`)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | OHOS 网络环境访问 GitHub 慢 | 使用 gitcode 镜像下载源码 |
| 2 | /tmp 只读 | OHOS 平台 /tmp 为只读文件系统 (E002) | 使用 $TMPDIR 或 $HOME/tmp |
| 3 | Maven 依赖下载慢 | 默认 Maven Central 在国内访问慢 | 配置阿里云 Maven 镜像源 |
| 4 | Gradle wrapper 路径解析失败 | wrapper 脚本使用相对路径, conan 构建目录与源码目录不同 | 直接使用系统 gradle 命令, 不使用 wrapper |
| 5 | conan-verify G2 "can't fork" | self.run() 传入限制性 env 参数, 丢失了必要的 PATH 等环境变量 | 直接修改 os.environ 而非传 env 参数 |
| 6 | Python str.format() 解析 shell 变量 | wrapper 脚本中 `${JAVA_HOME}` 的花括号被 Python format 误解析为占位符 | 使用字符串拼接而非 .format() |

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| bishengjdk | 17.0.13 | JDK (运行时) |
| gradle | 9.6.1 | 构建工具 |

## 验证结果

```bash
# ktfmt --version
$ ktfmt --version
ktfmt: 0.64

# ktfmt --help
$ ktfmt --help
Usage: ktfmt [flags] <file>...

# ktfmt --google-style 格式化测试
$ echo 'fun main(){println("hello")}' > Test.kt
$ ktfmt --google-style Test.kt
Done formatting Test.kt
# 结果: 代码被正确格式化 (大括号换行, 缩进规范化)
```

conan-verify 8 道门禁结果:
- G0 (预构建风险评估): ✅ PASS
- G1 (配方完整性): ✅ PASS
- G2 (conan create): ✅ PASS
- G3 (系统同名库隔离): ✅ PASS
- G4 (产物完整性): ✅ PASS
- L2 (smoke test): ✅ PASS
- L4 (安全扫描): ✅ PASS
- L5 (产物基线): ✅ PASS

## 交付物

| 文件 | 说明 |
|------|------|
| `libexec/ktfmt-0.64-with-dependencies.jar` | Fat JAR (~68MB), 包含所有依赖 |
| `bin/ktfmt` | Shell wrapper 脚本, 调用 `java -jar` |

## 注意事项

- ktfmt 是 JVM 应用, 不是原生编译的 C/C++ 库, 不需要 compiler/build_type settings
- 运行时需要 bishengjdk 17+ (JDK 17)
- Fat JAR 体积较大 (~68MB), 因为打包了所有 Java 依赖
- wrapper 脚本会自动检测 JAVA_HOME, 默认使用 `$HOME/bishengjdk17`
