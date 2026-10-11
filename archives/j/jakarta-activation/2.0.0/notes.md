# jakarta-activation 2.0.0 适配笔记

## 编译环境
- **类型**: 纯 Java API（无 native 编译）
- **编译日期**: 2026-10-07
- **JDK**: bishengjdk 17.0.13（配方优先 `JAVA_HOME` / `~/bishengjdk17`，按仓库既有
  cmd-pkgs 路径自装；**HNP 自带的 `/data/service/hnp/bin/java` 在本环境启动失败**，
  见下「真机环境注意点」）
- **Maven**: apache-maven 3.9.11（配方自 repo1.maven.org 自取，sha256 钉校验；上游无 mvnw）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/j/jakarta-activation/2.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 下载 GitHub tarball（`jaf-api` tag `2.0.0`，sha256 `f89b9a5d…37fe`），
`strip_root=True`。上游仓库名是 **jaf-api**（制品坐标 `jakarta.activation:jakarta.activation-api:2.0.0`），
tag 不带 `v` 前缀、也不带 `-RELEASE` 后缀（`2.0.0` 探测即 200）。

### 2. 构建（build()）
```bash
mvn -pl activationapi -am clean package -B -DskipTests=false
```
- 根 pom 的 modules 为 `activation` + `activationapi`（`demo` 仅在 profile 下启用）：
  - `activation` —— 类 jar（`jakarta.activation-2.0.0.jar`，25 个源文件）
  - `activationapi` —— API jar（`jakarta.activation-api-2.0.0.jar`，由 maven-dependency-plugin
    从 `activation` 装配；该模块自身无源文件）
  `-am` 保证 `activation` 一并构建。
- `-DskipTests=false` 保持与其它 Maven 配方一致的门禁语义（本库上游无测试源，surefire 无用例）。

### 3. 打包（package()）
两个 JAR → `libexec/`；`LICENSE`/`NOTICE` → `licenses/`。
`package_info()`：`libdirs = ["libexec"]`。

## 上游测试

**上游无任何测试用例**（如实披露）：

| 项 | 值 |
|----|----|
| 测试源目录 | `find . -type d -name test` → **空** |
| activation 模块 | 25 个 main 源 / **0** 个 test 源 |
| activationapi 模块 | 0 个 main 源 / **0** 个 test 源 |
| 框架声明 | activation/pom.xml 声明了 junit + surefire，但**无测试类**，surefire 无用例可跑 |
| 上游通过率 | **N/A**（无口径，不虚构） |
| 适配侧验证 | `test_package` 28 项反射断言（消费者视角） |

## 真机环境注意点

- **HNP 自带 JVM 在本环境无法启动**：`/data/service/hnp/bin/java -version` 报
  `Error occurred during initialization of VM / Failed to mark memory page as executable`；
  用 C 探针验证过本机 **RWX mmap 与 mprotect(RX) 均成功**（非全局 W^X 限制），
  故判为该 JDK 构建在此环境不可用。
  解法：按仓库既有范式经 cmd-pkgs 自装 `~/bishengjdk17`（BiShengJDK 17.0.13），
  实测 `openjdk version "17.0.13" … OpenJDK 64-Bit Server VM BiSheng` 正常。
  配方 `_ensure_java()` 的检查顺序因此为 `JAVA_HOME` → `~/bishengjdk17` →
  `~/usr/local/bishengjdk17` → PATH，避免选中坏 JVM。
- **HMDFS 执行位限制**：home 目录下新写入的可执行文件可能因 HMDFS 忽略执行位而
  「Permission denied」——故不要把 JDK 二进制放在 home 下临时目录再执行。
