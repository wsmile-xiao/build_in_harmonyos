# auto64fto32f

Auto64Fto32F 是一个极简的 Java 源码转换库：把以 `double`（64 位浮点）编写的数值 Java 代码，
通过精心设计的关键字/正则替换，自动生成对应的 `float`（32 位浮点）版本源码。
它被 EJML、DDogleg 等数值计算项目用来同时维护 F64/F32 两套实现。

## 功能概述

- 递归搜索目录中所有 `*_F64.java` 文件，生成同目录的 `*_F32.java`
- 默认替换规则：`double→float`、`Double→Float`、`_F64→_F32`、
  `Math.→(float)Math.`、浮点字面量自动追加 `f` 后缀（如 `1.6→1.6f`）
- 支持四种过滤器的自定义扩展：REGEX 替换、前缀替换、浮点字面量改写、后置 REGEX 还原
- `/**/` 前缀可豁免单个 token；`//CUSTOM ignore <token>` 可按文件忽略指定关键字；
  `//NOFILTER` 行级豁免
- `AugmentJavaFiles` 可为生成的 F32 类自动添加 `javax.annotation.Generated` 标记
- 支持 Java 与 Kotlin 两种目标语言（`Language.JAVA` / `Language.KOTLIN`）

## OHOS 适配

- **构建系统**: 上游使用 Gradle 6.4.1 构建。适配配方绕开 Gradle（其发行版下载与
  daemon 在鸿蒙真机上开销大且不稳），直接用 bishengjdk 的 `javac` 编译
  `src/` 下 4 个源文件并打成 JAR，语义与上游 `gradle assemble` 一致
- **上游测试**: 上游唯一测试套件为 JUnit 4 的 `TestAugmentJavaFiles`（4 个 @Test 方法），
  配方在 `build()` 中直接以 `org.junit.runner.JUnitCore` 运行，JUnit/hamcrest 从
  Maven Central 获取并做 sha256 校验
- **运行时**: 纯 JVM 库，无原生代码；运行需 JDK 17+（bishengjdk17，可通过 cmd-pkgs
  install-jdk.sh 安装）
- **产物形态**: `libexec/auto64fto32f-2.1.jar`，无 bin/ 可执行入口（上游 src/ 无 main class，
  属于被构建脚本引用的代码生成库），因此不需要 commands.json

## 依赖

- 编译期: 无第三方依赖（纯 JDK）
- 测试期: junit 4.12 + hamcrest-core 1.3（Maven Central）
- 运行期: bishengjdk 17+（系统工具，非 Conan 包）

## 参考

- 官方仓库: https://github.com/lessthanoptimal/Auto64Fto32F
- 许可证: Unlicense 或 MIT 双许可（可任选）
