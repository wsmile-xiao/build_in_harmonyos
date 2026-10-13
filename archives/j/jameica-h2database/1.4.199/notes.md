# jameica-h2database 1.4.199 — 适配笔记（OHOS / HarmonyOS PC）

## 1. 选它的理由

比赛清单条目「jameica-h2database 1.4.199」= Debian 为 Jameica 重打包的 **H2 数据库引擎**。
Debian 源包 Build-Depends 仅 `debhelper-compat / default-jdk / javahelper` → **无外部库依赖**，
适配只需一个 JDK（本环境用 `~/bishengjdk17`），属"零依赖"档，故在剩余候选里优先做它。

（同批筛掉的：`interception-dual-function`/`jedi-language`/`jellyfin-mpv` 在 Debian **无源包**；
`jcabi-aspects` 需 libaspectj；`jameica-datasource` 需 maven-debian-helper + jameica。）

## 2. 源码与版本取值

| 项 | 实际 |
|---|---|
| 源包 | `jameica-h2database_1.4.199.orig.tar.xz`（Debian pool，2395812 B） |
| sha256 | `681d425b422e14f7e2db26188d19ab90eb0226f96c254bc4b0e118b9c149eb5b` |
| 顶层目录 | `h2database-1.4.199/` |
| 版本差异（如实披露） | 该树 pom.xml 版本写作 **`1.4.200-SNAPSHOT`**（H2 发布后即顶到下一 SNAPSHOT 的惯例）→ 交付名按 Debian 源包版本取 **`h2-1.4.199.jar`** |

## 3. 关键认知：零运行期依赖 ≠ 零编译期依赖

H2 核心 jar **运行期零依赖**（`java.sql` 即用），但 `src/main` 里含**可选集成类**，
编译它们需要 5 族 API（**上游发布 jar 也是这么编的**，其 pom 同样声明；故本适配照做，
但**只用于编译、不进产物**）：

| API | 用到它的主源码 | 版本（钉 sha256） |
|---|---|---|
| servlet | `org/h2/server/web/WebServlet.java` | javax.servlet-api **3.1.0** |
| OSGi core / enterprise | `org/h2/util/DbDriverActivator.java`、`OsgiDataSourceFactory.java` | **4.2.0 / 4.2.0**（**必须与 pom 的 `<osgi.version>4.2.0` 对齐**） |
| JTS | `org/h2/util/geometry/JTSUtils.java` | jts-core **1.15.0** |
| Lucene | `org/h2/fulltext/FullTextLucene.java` | lucene-core / analyzers-common / queryparser **5.5.5** |
| slf4j | `org/h2/message/TraceWriterAdapter.java` | slf4j-api **1.7.25** |

踩过的坑（都已写进知识草稿）：
- 只给 `org.osgi.core` 不够 → `OsgiDataSourceFactory` 用的是 **service/enterprise** API；
- 给 6.0.0/5.0.0 也不行 → `registerService(String,…)` **签名随版本变化**，必须 4.2.0；
- 一次把主源码里**全部**第三方 import 列清（`org.apache`/`org.locationtech`/`javax.servlet`/
  `org.osgi`/`org.slf4j`；其余 `javax.tools|script|crypto`、`org.xml|w3c` 都是 JDK 自带）后
  才一次配齐，避免反复试错。

## 4. 构建与打包

- **不用 Maven**：`javac` 编 `src/main` 全部 **615** 个 .java（classpath = 上述编译期 jar）→
  把 `src/main` 下所有**非 .java 资源**（`_messages_*.prop` 等）按相对路径并入 `classes/` →
  `jar cf h2-1.4.199.jar -C classes .`。
- 产物：`libexec/h2-1.4.199.jar`，**2301238 B**，sha256 `0e903b52…`（本地实测）。
- 无需补丁（`patches_applied: []`）。

## 5. 上游测试：具名工具链边界（不宣称通过率）

`src/test/org/h2/test/unit/` 共 **67** 个用例（H2 自研框架：每个类自带 `main()`，退出码即判定）。
配方按「**只放行 `org.h2.*` 与 JDK 自带**」的 import 口径筛可离线编译者，并做**传递闭包排除**
（引用到被排除用例的也排除）。实测仍有用例引用上游 **test-only 依赖**（`org.objectweb.asm` 等），
测试树编译不通过 → 配方按**具名工具链边界**如实记录并跳过运行：

```
[upstream tests] 具名工具链边界：测试树编译未通过（上游 test-only 依赖，如 ASM / ext 驱动，
本适配不引入）→ 未在 build 内真跑，**不宣称任何通过率**；
首个错误：…/TestKeywords.java:18: error: package org.objectweb.asm does not exist
```

即：**不冒充通过、也不把边界记成缺陷**（与 ink-generator 的 Rust 测试、jarchivelib 的
tar uid 上限同一披露口径）。

## 6. 消费者校验（全过）

`test_package/check_h2.py`（`checks=4 fails=0 skips=0` / `RESULT: PASS`）：
①产物齐备；②jar 合法 + 关键类（`org/h2/Driver`、`engine/Engine`、`command/Command`）与资源
（`org/h2/res/_messages_en.prop`、`META-INF/MANIFEST.MF`）齐备；③**端到端真跑**——仅用 JDK
自带 `java.sql` 驱动内存库 `jdbc:h2:mem:`，建表→插入→查询→读回 `atom`（`H2_E2E=atom`）；
④证据（大小/sha256/JDK）。

> 修正记录：初版把资源断言写成 `org/h2/res/help.csv`（**望文生义的错猜** ✗，实测报缺失）；
> 核过上游 `res/` 目录（只有 `_messages_*.prop` 与 png）后改为 `_messages_en.prop` ✓。

## 7. 网络注意事项（本环境实测）

Conan 的 `download()` 对 `repo1.maven.org` / `repo.maven.apache.org` 的这几个 jar
**反复 ReadTimeout**（`curl` 同一 URL 正常）→ 配方改用 `curl -fsSL --retry 3` 抓取并
**自算 sha256 校验**（不匹配即失败），并支持可选本地预置目录 `H2_COMPILE_JAR_DIR`
（sha256 一致才采用）；CI 不设该变量时走网络，行为一致。
