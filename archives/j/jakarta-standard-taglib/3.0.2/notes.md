# jakarta-standard-taglib 3.0.2 — 适配笔记（OHOS / HarmonyOS PC）

## 1. 为什么选它

比赛清单条目「jakarta-standard-taglib 3.0.2」对应 **JSTL（Jakarta Standard Tag Library）3.0.2**。
选它的理由：**零 Conan requires**（纯 Java 制品，无 C 库依赖、无私有工具链），
所有构建/测试期依赖都能在构建时从 Maven Central 自取——与已合入的
`archives/j/jakarta-inject-api/2.0.1`、`archives/j/jackson-core/2.14.1` 同一范式。

## 2. 源码来源与取证

| 渠道 | 实测 | 结论 |
|---|---|---|
| Debian 源包 `jakarta-standard-taglib` | `3.0.2-2`（trixie）/ `3.0.2-3`（sid、forky） | 采用 |
| `jakarta-standard-taglib_3.0.2.orig.tar.xz` | sha256 `82db2bde4a180d0952fc66116aca78cf2d3e0e210bd0e01f72e46813ad111289`，291580 B | 作为源码（顶层目录 `jakarta-standard-taglib-3.0.2/`） |

Debian 同时存在 `src`（`3.0.2.orig.tar.xz`，与上游发布树一致）与 `src.tar.xz`，
本配方取 `orig.tar.xz`（更贴近上游）。

## 3. 依赖闭包实测（判「无缺口」的依据）

对本项目 4 个模块 pom（根 / api / impl / spec / tagsdoc）做了坐标抽取 +
在 Maven Central 上逐个 **HEAD 实测**：

| 坐标 | 版本 | scope | Maven Central |
|---|---|---|---|
| `jakarta.el:jakarta.el-api` | 5.0.0 | compile / provided | 200 ✓ |
| `jakarta.servlet:jakarta.servlet-api` | 6.0.0 | compile / provided | 200 ✓ |
| `jakarta.servlet.jsp:jakarta.servlet.jsp-api` | 3.1.0 | provided | 200 ✓ |
| `jakarta.servlet.jsp.jstl:jakarta.servlet.jsp.jstl-api` | 3.0.0 | provided（impl 用） | 200 ✓ |
| `xalan:xalan` | 2.7.3 | compile（impl 用） | 200 ✓ |
| `org.junit.jupiter:junit-jupiter-engine` | 5.8.2 | test | 200 ✓ |

- 唯一的 "404" 是 **本项目自己的 `org.glassfish.web:tagsdoc:1.0-SNAPSHOT`** —— 属 reactor 内模块（文档模块），
  **不是外部缺口**；
- `asciidoctorj` / `asciidoctorj-pdf` / `jruby-complete` 只出现在 `tagsdoc`（文档）模块，**不在构建范围**。

⇒ **结论：零 Conan requires，无依赖缺口**（构建/测试期依赖全部由 Maven 自取）。

## 4. 构建与打包口径

- 模块：**只 build `api` + `impl`**（`mvn -pl api,impl -am`）——`spec` 是文档模块、
  `tagsdoc` 是 asciidoctor 文档模块，都不是要发布的制品（reactor 裁剪在此合理；
  注意与「**裁剪会改变产物来源**」那条知识（jakarta-activation 的 C5C1）区分：
  本例裁剪掉的是文档模块，未影响被发布制品的编译来源）。
- 产物：
  - `api`：`jakarta.servlet.jsp.jstl-api-3.0.2.jar`
  - `impl`：上游 impl pom 自身版本是 **`3.0.2-SNAPSHOT`**，jar 名带 `-SNAPSHOT`；
    配方在 `package()` 里定位后**重命名**为 `jakarta.servlet.jsp.jstl-3.0.2.jar`
    （jar 内 MANIFEST 与此无关，不影响使用）。
- 工具链：`bishengjdk17`（JAVA_HOME → `~/bishengjdk17` → `~/usr/local/bishengjdk17` → PATH）
  与 `apache-maven 3.9.11`（自 `repo1.maven.org` 自取 + sha256 校验），与同域配方一致。
- JDK 17 风险预判：本项目用的是 `maven-bundle-plugin **5.1.3**`（不是会抛 CME 的 4.2.1），
  故未随包提交 bundle 插件升级补丁；若实测出现 javadoc doclint 报错再按同域先例补丁。

## 5. 测试口径

- **上游测试**：`impl` 模块带 JUnit 5 单测（`EvaluationTest` / `FunctionTest` / `ParserTest` +
  `TestUtilities`/`Bean*` 辅助类），由 surefire 真跑；`build()` 内解析
  `impl/target/surefire-reports/*.txt` 的 `Tests run/Failures/Errors/Skipped` 并**硬断言**：
  ①报告目录/文件缺失 → 判"上游测试未真跑"，直接失败；②`Tests run=0` → 拒绝宣称成功；
  ③`Failures>0 || Errors>0` → 判真实失败并中止构建（不玩"只统计通过"）。
- **消费者校验**（`test_package/`）：产物齐备 / 两个 jar 均为合法 zip 且含关键类 /
  MANIFEST 存在 / **端到端真跑**（`javac` + `java`，classpath = 两个包内 jar + 从 Maven
  **自取并 sha256 钉校验**的 `jakarta.servlet-api-6.0.0.jar`、`jakarta.servlet.jsp-api-3.1.0.jar`、
  `jakarta.el-api-5.0.0.jar`），调用 impl 侧真实的 JSTL EL 函数并断言返回值。
  输出统一 `checks= / fails= / skips=` 三计数；SKIP 仅限**具名环境信号**（本环境无网络等），
  其余（未识别的非 0 退出、真实闭包/符号缺陷）一律判 FAIL。

## 6. 实测结果（本地 conan create，2026-10-08）

- **构建**：`BUILD SUCCESS`（api + impl 单 reactor）→ `Package '6b129b06…' created`
  （revision `35cca132…`），产物 api 46227 B / impl 4024776 B，均入 `libexec/`。
- **上游测试**：surefire `reports=3  Tests run=3 Failures=0 Errors=0 Skipped=0`（**3/3 通过**）——
  ParserTest / EvaluationTest / FunctionTest 各 1 条，真跑。
- **消费者校验**：`checks=5 fails=0 skips=0` / `RESULT: PASS`，其中端到端为
  `Functions.toUpperCase("atom") == "ATOM"`（javac + java，classpath = 包内两 jar + 3 个自取容器 API jar）。
- **补丁**：**无需任何补丁**（本项目用 maven-bundle-plugin 5.1.3，无 4.2.1 的 CME 问题；
  `spec-version-maven-plugin 2.1` 在 JDK 17 下亦未报错）。
- `manifest.yaml` 已按上述实测数字填写（不预填假设值）。

