# jakarta-validation-api 3.0.2 — 适配笔记

## 概述
Jakarta Bean Validation 3.0（JSR-380）标准 API——纯 Java 注解/接口/异常库，**无实现**
（约束注解 `validatedBy` 均为空集，`@NotNull` 是通用约束，校验器由引擎内置）。
上游单 Maven 模块：`src/main/java`（98 个 .java）+ `src/test/java`（7 个 .java）+ 根 `pom.xml`。
需要 JVM 运行环境（bishengjdk 17）。本 PR 采用源码编译方式，使用 Maven 构建。

## 构建方式
- 类型：源码编译（单 Maven 模块，根目录一次 `mvn clean package -B -DskipTests=false`）
- 来源：GitHub tarball (https://github.com/jakartaee/validation/archive/refs/tags/3.0.2.tar.gz)
- SHA256: 27e45a524d60af32f62f08dd236357323dc976fba130ad1f565257c93d271a62
- 构建工具：Maven 3.9.11（上游无 mvnw wrapper，配方自取二进制并 sha256 校验）
- Java: bishengjdk 17.0.13
- 许可证: Apache-2.0（根目录 license.txt / NOTICE.md → licenses/）
- Maven 依赖通道：阿里云 central 镜像 settings.xml + 3 次重试 + 直连兜底
  （jakarta-authentication-api 先例：CI 直连 repo1.maven.org 报 Connection reset）

## 补丁
**无补丁。**
- maven-bundle-plugin 上游 pin **3.5.0**——早于 jakarta-inject-api 踩坑的 4.2.1
  （bnd/ZipFile ConcurrentModificationException 由 4.x 后期 bnd 引入），3.5.0 的
  bnd 无该问题，本地 JDK 17.0.17 构建实证通过。
- javadoc 注释在 JDK 17.0.17 上 doclint 全过（无 heading-sequence 问题），无需
  `<doclint>none</doclint>`（cdi 的 0001 补丁不适用于本仓库）。
- 本地全量构建：BUILD SUCCESS，Tests run: 10, Failures/Errors/Skipped 全 0（2026-09-29）。

## 上游测试
- **10 个 TestNG 方法，2 个测试类**：`ConstraintViolationExceptionTest` 3 个 +
  `ValidationTest` 7 个；`examples/` 2 类（ConstraintValidationNodeBuilderTest /
  NodeTraversalTest）是 main() 演示、零 @Test；3 个 SPI provider fixture
  （BarValidationProvider / FooValidationProvider / NonRegisteredValidationProvider）无测试。
- 源码证据：`target/surefire-reports/junitreports/TEST-*.xml` 2 份，tests 求和 = 10，
  failures=0 / errors=0 / skipped=0；`testng-results.xml` 套件汇总 Tests run: 10。
- 构建命令：`mvn clean package -B -DskipTests=false`（package 阶段编译主源码 +
  javadoc + sources + jar，并运行上述 10 个测试；surefire forkMode=once、
  redirectTestOutputToFile=true 为上游原配置）。
- surefire includes 为 `**/*Test.java`：2 个零 @Test 的 examples 类不产生测试计数，
  与实测口径一致。

## 产物
- `target/jakarta.validation-api-3.0.2.jar` → `libexec/`
- 同一 package 阶段还产出 sources/javadoc jar（均不打包，仅主 jar 进 libexec/）。
- API 无实现：`Validation.buildDefaultValidatorFactory()` 在无 provider 的 classpath
  上按 spec 抛 `ValidationException`（test_package 负向断言覆盖）。

## test_package 测试
- `TestJakartaValidation.java`：纯反射探针，**35 断言**：
  - 1-21 类型加载：Valid/Validator/ValidatorFactory/ConstraintViolation/
    ConstraintViolationException/Path/ConstraintValidator/ConstraintValidatorContext/
    ValidationException/Validation/Configuration/bootstrap.GenericBootstrap/
    bootstrap.ProviderSpecificBootstrap/groups.Default/
    constraints.NotNull/Size/Min/Pattern/metadata.ConstraintDescriptor/
    executable.ExecutableValidator/valueextraction.ValueExtractor
  - 20 @Valid 是 RUNTIME 注解
  - 21 @Valid @Target 恰为五元素 {METHOD, FIELD, CONSTRUCTOR, PARAMETER, TYPE_USE}
    （上游源码实证，无 TYPE）
  - 22 @NotNull 带 @Constraint 元注解
  - 23 @NotNull.message() 默认模板 `{jakarta.validation.constraints.NotNull.message}`
  - 24 @Size min()=0 / max()=Integer.MAX_VALUE 默认
  - 25 @Min.value() 必填 long 无默认（源码实证）
  - 26 @Pattern.regexp() 必填无默认 / flags() 默认空数组
  - 27 Validator.validate(T, Class<?>...) 变参返回 Set
  - 28 ConstraintViolationException 继承 RuntimeException + getConstraintViolations()
  - 29 ValidationException 继承 RuntimeException
  - 30 Path.Node 接口契约（getName/getKind/isInIterable）
  - 31 ConstraintValidator.initialize 为 default 方法
  - 32 groups.Default 是接口
  - 33 负向引导：无 provider 时 buildDefaultValidatorFactory() 抛 ValidationException
  - 所有注解契约断言对照上游 3.0.2 源码逐条实证。
- `ConsumerValidationTest.java`：**最小 Bean Validation 引擎**消费者用例，10 个 E2E：
  - 引擎实现 Validator/ConstraintViolation/Path/Path.Node/ConstraintValidator 全部 SPI，
    注解类型→校验器工厂映射，消费 @NotNull/@Size/@Min 真实注解属性
  - E2E-1 合法对象零违规；E2E-2 @NotNull 违规报告契约（propertyPath/invalidValue/
    消息模板/rootBean）；E2E-3 @Size 三态（0 字符/11 字符违规、10 字符边界通过）；
    E2E-4 @Min 边界（17 违规/18 通过）；E2E-5 多字段同违规不短路（恰 3 条）；
    E2E-6 无跨对象状态残留；E2E-7 ConstraintViolationException 防御性拷贝同一违规集
    （上游源码实证 `new HashSet<>(constraintViolations)`）；E2E-8 注解属性与引擎消费一致；
    E2E-9 校验器工厂映射与真实判定（initialize 消费注解属性）；E2E-10 Validator 接口契约 + unwrap 语义
  - 每例独立 TEST PASS/FAIL + E2E TEST SUMMARY，任一失败 exit 1
- `test.sh`：JAR 存在性 + javac（`-encoding UTF-8`）双文件编译 + 两个程序运行 +
  PASS/SUMMARY 校验。
- 断言总数 **58** = 上游 10 + test_package 48（1 JAR + 1 编译 + 35 反射 + 10 E2E + 1 PASS）。

## 本地预检（Windows + JDK 17.0.17，非真机）
- 全量构建：`mvn clean package -B -DskipTests=false` → BUILD SUCCESS（3:46），
  Tests run: 10, Failures/Errors/Skipped 全 0；三 jar 产物齐全（主/sources/javadoc）。
- test_package 探针与消费者用例：用构建产出的 jar，`javac -encoding UTF-8` 编译 +
  java 运行，**35/35 反射断言 + 10/10 E2E 全过（rc=0）**（2026-09-29）。
- 负向对照：仅 JDK classpath（无 API jar）时编译失败，证明探针非空转。

## 真机验证（HarmonyOS PC aarch64，2026-09-29 23:04 通过）

- **conan-verify 八门禁 Verdict PASS**：G0 预构建评估 / G1 配方完整性（name/version/
  source/build/package/package_info/export_sources/补丁调用/R26 无静态链接/R28 test_package/
  MANIFEST.yml）/ G2 conan create 成功 / G3 无系统同名库冲突 / G4 产物完整性 / L2 平台冒烟
  （纯库跳过）/ L4 静态安全扫描（纯库跳过）/ L5 产物基线对比（纯库跳过）。
  R46 终态 result.json 已上报（draft:false），可标记 status: published。
- **构建**：真机 bishengjdk 17 + 配方自取 Maven 3.9.11（缓存命中 ~/apache-maven-3.9.11），
  `mvn clean package -B -DskipTests=false` BUILD SUCCESS，上游 Tests run: 10,
  Failures/Errors/Skipped 全 0（7.308s）。
- **产物**：package() 打包 1 jar（jakarta.validation-api-3.0.2.jar）+ license.txt + NOTICE.md
  → libexec/ 与 licenses/。
- **test_package**：`test.sh` 真机执行 —— JAR 存在性 OK；javac 双文件编译通过；
  探针 `PASS: jakarta.validation API test - 35 reflection assertions`；
  消费者 `E2E TEST SUMMARY: 10 passed, 0 failed` + `PASS: jakarta.validation consumer E2E`。
- **官方验收口径**：`python3 scripts/ohc-run.py conan-verify jakarta-validation-api 3.0.2`
  → `✅ 配方验证通过`（reports/conan-verify-report.md 随档；构建日志 conan-create.log 不随档，留本机）。
- **真机坑位新增（实录）**：
  - ohc-run.py 的 G2 会对含 github.com 的 conandata **注入 ghfast.top 镜像（E017 预防）**，
    而 ghfast.top 已挂（ReadTimeout+ConnectTimeout 双证）→ 真机验证时设备侧副本 URL 临时改指
    PC 本地 http.server 镜像（192.168.43.12:18081，PC 与真机同热点网段，字节级一致的官方
    tarball），无 github.com 串则不触发注入；sha256 不变，conan get() 仍钉校验。
    提交版 conandata 保持官方 GitHub URL 不变（MR 要求 R39 原始 URL）。
  - 设备 $HOME 在 /data/storage/el2/base 与 /storage/Users/currentUser 之间漂移：
    xfer 落点与 shell 的 cwd 不一定一致 → xfer 用 MSYS_NO_PATHCONV=1 + 设备绝对路径，
    脚本内部统一 export HOME=/storage/Users/currentUser 并全部绝对路径引用。
  - 设备侧中继脚本（nohup 起）会被 OHOS 会话清理 SIGTERM：其派生的 shell 存活但不再重连 →
    长命令用 run_devN_long（连接全程保持，防孤儿）。
  - 中继通道共享污染：通道3 被其他会话的 kddockwidgets 验证占用 → 本任务新建私有通道
    （4460/4461，server6.py + r6.py + run_dev6/xfer_dev6），互不串扰。

## 注意事项
- 纯 Java API 库，需要 JVM 运行环境（bishengjdk 17）
- 构建需要网络（Maven 下载依赖与插件、配方自取 Maven 二进制）
- JAR 存放在 libexec/ 目录，通过 cpp_info.libdirs 导出
- JAVA_HOME 优先取环境变量，其次检测常见 JDK 路径，缺失时经 cmd-pkgs 自动安装
- settings 声明完整四项（os/compiler/build_type/arch）：Java 包不消费编译设置，
  但 CI 的 L0p 门禁要求 OHOS profile 四项齐全（缺 compiler/build_type 直接判失败），
  四项只进 package_id，build() 不读
- 真机坑位已内置（jakarta-cdi-api 4.0.1 实踩）：Maven 自取 curl→python3 urllib
  免证书回退 + sha256 钉校验；HMDFS 禁 shebang→显式 `sh {maven_home}/bin/mvn`
