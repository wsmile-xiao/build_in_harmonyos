# jakarta-servlet-api 6.1.0 适配笔记

## 编译环境
- **类型**: 纯 Java API（无 native 编译）
- **编译日期**: 2026-10-07
- **JDK**: bishengjdk 17.0.13（配方经 cmd-pkgs 自取；系统自带 java 在真机不可用，见下）
- **Maven**: apache-maven 3.9.11（配方自 repo1.maven.org 自取，sha256 钉校验；上游无 mvnw）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/j/jakarta-servlet-api/6.1.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 下载 GitHub tarball（`6.1.0-RELEASE`，sha256 `1f1fa965…7961`），`strip_root=True`。

**注意 tag 形态**：该仓库 release tag 带 `-RELEASE` 后缀——`6.1.0`、`v6.1.0` 探测均 404，
只有 `6.1.0-RELEASE` 为 200。

### 2. 构建（build()）
```bash
mvn -pl api -am clean package -B -DskipTests=false
```
- 根 pom 的 modules 为 `api` / `spec` / `tck`：
  - `api` —— 制品来源（`jakarta.servlet-api-6.1.0.jar`）
  - `spec` —— 文档模块（asciidoctor 出 PDF/HTML），不打包
  - `tck` —— 完整 Servlet TCK（独立大工程），不打包
  故用 `-pl api -am` 只构建 api 及其父 pom，避免把 TCK 拉进来。
- `-DskipTests=false` 让上游 JUnit 5 测试在 package 阶段由 surefire 3.2.5 执行。

### 3. 打包（package()）
`api/target/jakarta.servlet-api-6.1.0.jar` → `libexec/`；`LICENSE`/`NOTICE` → `licenses/`。
`package_info()`：`libdirs = ["libexec"]`。

## 上游测试

| 项 | 值 |
|----|----|
| 测试源文件（api 模块） | 10 个 = 3 个测试类 + 7 个 mock/辅助类 |
| 测试类 | CookieTest、CanonicalUriPathTest、HttpServletTest |
| 测试方法 | 12 个 `@Test` + 5 个 `@ParameterizedTest` = 17 个 |
| 框架 | JUnit 5（junit-jupiter 5.10.2 + hamcrest 2.2），surefire 3.2.5 |
| 执行命令 | `mvn -pl api -am clean package -B -DskipTests=false` |

## 真机环境注意点

- **系统自带 `java` 不可用**：`/data/service/hnp/bin/java -version` 报
  `Error occurred during initialization of VM / Failed to mark memory page as
  executable - check if grsecurity/PaX is enabled`——因此配方沿用既有范式
  `_ensure_java()`：优先 `JAVA_HOME`，其次常见路径，最后经 cmd-pkgs 自取
  bishengjdk 17.0.13。
- **HMDFS 执行位限制**：`/storage/Users/currentUser` 下的可执行文件可能因
  HMDFS 忽略 chmod 而无法直接执行（实测 `tmp/jdk-22.0.1/bin/java` 报
  Permission denied）——故依赖配方从 `~/bishengjdk17`（cmd-pkgs 安装路径）取 JDK。
