# jakarta-activation 2.0.0

## 软件描述
Jakarta Activation 2.0（原 JavaBeans Activation Framework，JAF）提供与数据类型无关的数据访问与命令映射 API：`DataHandler` 统一读写任意 MIME 数据、`DataSource` 抽象数据来源、`CommandMap`/`CommandInfo` 做 MIME 到命令的映射、`FileTypeMap` 做文件后缀到 MIME 映射、`ActivationDataFlavor` 描述可传输数据形态。

## 功能概述
- **数据处理**：`DataHandler`、`DataContentHandler`、`DataContentHandlerFactory`
- **数据来源**：`DataSource`（接口）、`FileDataSource`、`URLDataSource`
- **命令映射**：`CommandMap`（抽象）、`MailcapCommandMap`、`CommandInfo`
- **类型映射**：`FileTypeMap`（抽象）、`MimetypesFileTypeMap`
- **MIME 与传输**：`MimeType`、`MimeTypeParseException`、`ActivationDataFlavor`、`UnsupportedDataTypeException`

## OHOS 适配

### 构建方式
- **纯 Java API**（无 native）：GitHub tarball 源码 + Maven 编译，产出**两个 JAR** 入 `libexec/`：
  - `jakarta.activation-api-2.0.0.jar`（API jar，由 `activationapi` 模块经 maven-dependency-plugin 装配）
  - `jakarta.activation-2.0.0.jar`（类 jar，来自 `activation` 模块）
  ——同 `jakarta-cdi-api` 4.0.1 / `jakarta-servlet-api` 6.1.0 的既有范式
- **reactor 作用域**：根 pom 的 modules 为 `activation` + `activationapi`（`demo` 仅在 profile 下启用）——用 `-pl activationapi -am` 只构建这两个模块
- **工具链自取**：上游无 mvnw——配方经 cmd-pkgs 自取 bishengjdk 17.0.13，并从 repo1.maven.org 取 apache-maven 3.9.11（sha256 钉校验）

### 关键点
1. **上游无测试源**：`find . -type d -name test` 为空（`activation` 25 main / 0 test，`activationapi` 0/0）——因此**没有上游测试可跑、上游通过率记 N/A**（如实披露，不虚构）；消费者验证由 `test_package` 的 28 项反射断言承担
2. **HNP 自带 JVM 不可用**：`/data/service/hnp/bin/java` 在部分环境启动即失败
   （`Failed to mark memory page as executable`）；按仓库既有 cmd-pkgs 路径自装的
   `~/bishengjdk17`（BiShengJDK 17.0.13）正常——故配方 `_ensure_java()` 优先
   `JAVA_HOME` / `~/bishengjdk17`，最后才回退 PATH
3. **`package_info()`**：`libdirs = ["libexec"]`，消费者把两个 JAR 加入 classpath

### 与 Linux 的差异
无差异——纯 Java API（无 native、无平台相关代码），全平台一致。

## 依赖关系
- **构建期**：bishengjdk 17.0.13 + apache-maven 3.9.11（配方自取，不产生 Conan 依赖）
- **运行期**：无（API JAR；消费者按需与其它 Jakarta EE API 组合）

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 2.0.0 | built | 2026-10-07 | 源码编译 activation + activationapi 两个模块，双 JAR 入 libexec；上游无测试源 |

## 参考资料
- 上游仓库: https://github.com/jakartaee/jaf-api
- 规范页面: https://jakarta.ee/specifications/activation/2.0/
