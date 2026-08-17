# JFlex 1.9.1 HarmonyOS 前置适配记录

## 状态

- issue: `2241`
- 分支: `feat/jflex-1.9.1-2241`
- worktree: `D:\\harmonyos\\worktrees\\jflex`
- 当前状态: 配方与消费者测试已准备；本机缺 Conan/JDK，尚未完成真机构建。
- manifest 暂记 `failed`，真机 `conan create` 通过后再改为 `built`。

## W0 依赖检查

- Conan 必选依赖: 无。
- Conan 可选依赖: 无。
- 运行/构建环境: JDK 11+；OHOS 采用仓库既有的 BishengJDK 17.0.13。
- 构建工具: 优先使用真机已有 Maven；不存在时由配方下载并校验 Apache Maven 3.6.3。
- Maven 构建会从 Maven Central 获取 CUP runtime、Ant、JSR-305、AutoValue 注解及 JUnit/Truth/Quickcheck 测试依赖。这些是 Java 构建依赖，不是本仓库 Conan 依赖，不混入本 PR。
- 已用会话隔离的 Conan 2.29.1 确认配方依赖图为空；查询 `ohpcd` 时服务端返回 `system acceleration policy not enabled`，未进入包存在性判断，因此同版本占用仍待真机确认。

## 源码与构建系统

官方发布包同时包含 `pom.xml`、`BUILD.bazel`、源码、测试与预编译 full JAR。
本配方选择 Maven：`mvn clean package -B -DskipTests=false` 会先运行 JUnit 4/Surefire 上游测试，再由 maven-shade-plugin 生成包含 CUP runtime 的 `target/jflex-full-1.9.1.jar`。

源码审计结果：

- 官方发布包 SHA256: `e0c1e9eef91ff6df04d73fa5eaff13f3a02b679fee1474e5ccae007224df6df6`
- 官方 SHA1 与本机下载一致: `a0f90647a2d7e48ac0fb7bb2e787a12b0b4af19a`
- `src/test/java` 共 19 个 Java 文件；Surefire include 规则匹配 12 个 `*Test.java` / `*Tests.java` / `*Quickcheck.java` 测试源文件。
- 静态审计识别到 50 个 JUnit 3 风格 `test*()` 方法；Quickcheck 的真实展开数量以真机 Surefire XML 为准。
- 未发现需要 OHOS 源码补丁的本机前置证据。

## test_package

消费者测试执行完整工具链：

1. `java -jar ... --version` 验证版本。
2. 用打包后的 JFlex 从 `Lexer.flex` 生成 `GeneratedLexer.java`。
3. 用 BishengJDK `javac` 编译生成 lexer 与 `TestLexer.java`。
4. 运行 lexer，断言 `sum+42 value` 被识别为标识符、加号、整数、标识符。
5. 输出 `HMBS_TEST_PACKAGE_RESULT`；上游 Maven 测试输出 `HMBS_UPSTREAM_TEST_RESULT`，计数来自 Surefire XML。

## 本机验证边界

已完成：官方资产 SHA256/SHA1、解包结构、Maven/Bazel 定义、JAR 主类/CUP runtime、测试清单审计，以及 Conan 2.29.1 的 `inspect`、Linux-armv8 `graph info`、`export`、`source`（官方源约 159 秒后成功）和 Python/YAML 静态检查。
未完成：本机无 Java/Maven，不能执行 `conan create` 或 Java 消费者测试；`ohpcd` 查询受远端 acceleration policy 阻断。

## 下一步真机 / shadow CI

先确认隔离 Conan 配置、JDK 和包占用：

```sh
conan profile show -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64
test -x "$HOME/bishengjdk17/bin/java" || test -x "$HOME/usr/local/bishengjdk17/bin/java"
conan download "jflex/1.9.1" -r=ohpcd --only-recipe
```

同版本不存在时执行单包验证：

```sh
CI_PACKAGES="archives/j/jflex/1.9.1" zsh ci/conan/build_and_test.sh
# 或 shadow runner:
/path/to/run-ohos-shadow-ci.sh archives/j/jflex/1.9.1
```

若直接验证配方：

```sh
conan create archives/j/jflex/1.9.1 --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## Real-device shadow CI result

- Final run: `codex-jflex-jflex-1.9.1-2241-b-shadow-r4-20260817-132158-24356`, exit code 0, isolated HOME/CONAN_HOME/TMPDIR, OHOS armv8 profile.
- Upstream Maven/Surefire: 133 executed, 132 passed, 0 failed, 1 skipped; Maven build succeeded.
- Consumer test: 19/19 checks passed through `tool_requires` for buildenv paths, two generations, javac compilation, basic semantics, Unicode text, and lexical-state transitions.
- Gates: L0 pass, L1 pass, L2 expected skip (no native `bin/`), L4 pass, L5 non-blocking warning (`libexec` JVM artifact).

Observed run history:
- r1: try-lock returned 75 while another package held the device lock.
- r2: L0 exposed missing compiler/build_type settings and inappropriate CLI classification.
- r3: Conan rejected library package type without a shared option; changed to build-scripts.
- r4: JDK installer download exposed the worker CA bundle requirement.
- r5: direct execution of the extracted Maven shell script returned EACCES.
- r6: full cold shadow CI passed after CA propagation, installer SHA256 pinning, and explicit `sh mvn` execution.

## Path B build-tool enhancement

The package now exposes a reusable Conan build-tool contract instead of
requiring every downstream recipe to discover the package folder and assemble
`java -jar` manually:

- `jflex.sh` is packaged next to the full JAR under `libexec/` and resolves Java from `JAVA_HOME` or `PATH`.
- `package_info()` publishes `JFLEX_JAR`, `JFLEX_COMMAND`, and `JFLEX_VERSION` through `buildenv_info`.
- Consumers declare JFlex with `tool_requires` and invoke `sh "$JFLEX_COMMAND"` under `env="conanbuild"`.
- `test_package` expands from 8 checks to 19 checks across a basic lexer and a Unicode/stateful lexer.

Enhancement run history:

- b-r1: L0 rejected an explicit empty `bindirs` declaration as a CLI signal; the declaration was removed without adding out-of-scope `commands.json`.
- b-r2: global `--try-lock` returned 75 while another package held the device.
- b-r3: cold build and all 133 upstream cases completed, then test_package exposed that `jflex.sh` must be copied from `export_sources_folder`.
- b-r4: full pipeline passed in 10m23s: upstream 132 passed/1 skipped and consumer 19/19; L0/L1/L4 passed, L2 skipped, and L5 warned as expected.
