# jakarta-annotation-api 2.1.1 — 适配笔记

## 概述
Jakarta Annotations 2.1（Common Annotations，原 JSR-250）标准 API——纯 Java 注解库，
**无实现、无行为**（注解仅作为容器/工具的元数据标记）。上游仓库
jakartaee/common-annotations-api 为多模块 Maven 工程：`api/`（19 个 .java，全部在
src/main）+ `spec/`（asciidoc 规范文档，无代码）。需要 JVM 运行环境（bishengjdk 17）。
本 PR 采用源码编译方式，仅构建 api/ 子模块，使用 Maven 构建。

## 构建方式
- 类型：源码编译（多模块仓库，仅构建 `api/` 子模块：`mvn -f api/pom.xml`，
  对齐上游 CI `.travis.yml` 的 `mvn -f api/pom.xml verify -B -V`；spec/ 为 asciidoc
  文档无代码产物）
- 来源：GitHub tarball (https://github.com/jakartaee/common-annotations-api/archive/refs/tags/2.1.1.tar.gz)
- SHA256: 06eccfd01cd59bb1d3778c13a12759363b0f58e5d05f97c68db83c9d703c57b5
- 构建工具：Maven 3.9.11（上游无 mvnw wrapper，配方自取二进制并 sha256 校验）
- Java: bishengjdk 17.0.13
- 许可证: EPL-2.0 OR GPL-2.0 WITH Classpath-exception-2.0（根目录 LICENSE.md /
  NOTICE.md → licenses/；注意与 inject/validation 的 Apache-2.0 不同）
- 父 POM: org.eclipse.ee4j:project:1.0.7（enforcer 要求 JDK 11+/Maven 3.6+）
- Maven 依赖通道：阿里云 central 镜像 settings.xml + 3 次重试 + 直连兜底
  （jakarta-validation-api 先例：CI 直连 repo1.maven.org 报 Connection reset）

## 补丁
**无补丁。**
- 上游 api/pom.xml 已固定 maven-bundle-plugin **5.1.1**（bnd 6.x）——不受 JDK 17.0.13+
  的 bnd/ZipFile ConcurrentModificationException 影响（jakarta-inject-api 踩坑的是
  4.2.1；validation-api 3.5.0 同样免补丁）。
- javadoc doclint 在本 JDK（17.0.13）下全过（无 heading-sequence 报错），无需
  `<doclint>none</doclint>`（cdi/inject 的 0001 补丁不适用于本仓库）。
- 本地全量试跑：BUILD SUCCESS，jar + sources + javadoc 三产物齐全（2026-10-08，
  日志 ~/ca-audit/trial-build.txt 1137 行）。

## 上游测试
**0 个测试方法（API-only 模块）**，三重证据：
- tarball 中 `api/src` 无 test 目录：19 个 .java 全部在 `src/main/java/`
  （jakarta.annotation 根包 9 + security 5 + sql 2 + 3 个 package-info/module-info
  非注解文件；产出 18 个 .class）。
- 试跑日志（~/ca-audit/trial-build.txt L993-997, L1124）：
  `compiler:3.8.1:testCompile — No sources to compile`；
  `surefire:3.2.5:test — No tests to run`。
- `.travis.yml` 仅 `mvn -f api/pom.xml verify -B -V`，无独立测试阶段；spec/ 为
  asciidoc 文档模块，无任何代码。
- 上游构建命令（含 test 阶段）：`mvn -f api/pom.xml clean package -B -DskipTests=false`

## 产物
- `api/target/jakarta.annotation-api-2.1.1.jar` → `libexec/`
- 同一 package 阶段还产出 sources/javadoc jar（均不打包，仅主 jar 进 libexec/）。
- jar 内容（实证）：18 个 .class = 根包 10（9 个注解 + Resource$AuthenticationType
  嵌套枚举；package-info.java 不产 class）+ security 5 + sql 2 + module-info.class 1
  （JPMS 模块名 `jakarta.annotation`）+ OSGi Manifest（Bundle-SymbolicName
  `jakarta.annotation-api`，Export-Package 三包 version="2.1.1"）+ 内嵌
  META-INF/LICENSE.md/NOTICE.md + maven pom 元数据。
- test_package 用类路径模式消费（非 module-path），与 JPMS/OSGi 双 manifest 兼容。

## test_package 测试
- `TestJakartaAnnotation.java`：纯反射探针，**53 断言**：
  - 14 个顶层注解类型加载（Generated/ManagedBean/Nonnull/Nullable/PostConstruct/
    PreDestroy/Priority/Resource/Resources/security×5/sql×2 中排除嵌套枚举）+ 1 枚举
    AuthenticationType + 2 根包补充（Nonnull/Nullable 单独核验）
  - 方法签名契约：Resource.name()/lookup()/type()、Priority.value()、Generated.value()
    （String[]）、RolesAllowed.value()
  - 元数据契约：@PostConstruct/@PreDestroy target=METHOD+RUNTIME+Documented、
    @Resource RUNTIME+Repeatable(Resources)+targets{TYPE,FIELD,METHOD}、@Generated
    SOURCE retention、@Priority RUNTIME+Documented、@ManagedBean @Deprecated（2.1.1
    新增）、@RolesAllowed/{TYPE,METHOD}、@RunAs TYPE only、@DataSourceDefinition
    Repeatable(DataSourceDefinitions)
  - 默认值契约：Resource.type()=Object.class、shareable()=true、authenticationType()
    =CONTAINER、lookup()/mappedName()/description()=""、Generated.date()=""、
    AuthenticationType 恰 {CONTAINER, APPLICATION}
- `ConsumerAnnotationTest.java`：**最小注解驱动容器**消费者用例，17 个 E2E：
  - 容器实现 @Resource 字段注入（显式 JNDI 名 + 无 name 默认字段名推导）+
    @PostConstruct 注入后回调 + @PreDestroy 销毁回调，lifecycle log 可观测
  - 注入值真实生效核验：反射读私有字段验证注入值来自绑定表
  - @Resource 属性消费：description()/shareable()=false 元数据读取
  - @Priority 拦截器排序语义（容器按注解值升序排 AuditInterceptor/LoggingInterceptor）
  - 安全注解：@RolesAllowed/@PermitAll/@RunAs/@DeclareRoles 元数据读取
  - @Repeatable(@Resources)：getAnnotationsByType 解析 2 条声明 + 容器注解直读
  - @Generated SOURCE retention：运行时不可见（规范语义）+ 注解类型自身元数据可读
  - 每例独立 OK/FAILED + E2E TEST SUMMARY，任一失败 exit 1
- `test.sh`：JAR 存在性 + javac（`-encoding UTF-8`）双文件编译 + 两个程序运行 +
  PASS/SUMMARY 校验；OHOS 环境探测行（uname grep ohos/openharmony）。
- 断言总数 **75** = test_package 75（1 JAR + 1 编译 + 53 反射 + 17 E2E + 2 程序
  PASS + 1 SUMMARY 0 failed）；上游 0。

## HarmonyOS PC 专项验证（test_ohos/，1 项逻辑测试，真机 1/1 PASS）
- 纯 Java 注解 jar **无平台 API 差异**（无 native 代码、无 sun.misc/内部 API 依赖、
  无 JNI、无平台条件分支）——不伪造 __OHOS__ 宏或平台专项，采用
  「目标平台 JVM + 最终 Conan 包 jar 消费」方式（`sh test_ohos/run_ohos_test.sh
  <pkg_dir>`，自包含可单独执行，T1-T5 内部断言整体计 1 项不重复计数）：
  - **T1** 定位 test_package 实际使用的 java（对齐 test_package/conanfile.py 的
    JAVA_HOME 探测链：env 优先 + ~/bishengjdk17 等候选），readlink 解析 symlink
    链至真实二进制；本次实证 usr/local/bin/java → ~/bishengjdk17/bin/java
    （ELF64 AArch64 DYN 即最终 native launcher，无脚本包装层）。
  - **T2/T3** fail-closed 验证真实 java 二进制 ELF64（Class: ELF64）+ AArch64
    （Machine: AArch64）；检查工具链 readelf → llvm-readelf → llvm-readobj
    （--elf-output-style=GNU）依次回退，三者皆缺时**明确失败退出，不 SKIP**；
    launcher 非 ELF 时打印首字节诊断（魔数 7f 45 4c 46），要求沿真实启动链
    找到最终 native launcher 重验，不降级标准。
  - **T4** 动态 ELF 时 PT_INTERP 必须为 musl AArch64 loader——本次实证
    `Requesting program interpreter: /lib/ld-musl-aarch64.so.1`；静态 ELF
    （无 PT_INTERP）则无需 loader 断言。
  - **T5** 在该已确认的 HarmonyOS AArch64 JVM（bishengjdk 17.0.13）下，用最终
    Conan 包 libexec/jakarta.annotation-api-2.1.1.jar 作 classpath 编译并运行
    OhosConsumer：JVM 自报 os.name=HarmonyOS / os.arch=aarch64 /
    os.version=HongMeng Kernel 1.12.0，真实消费 @Resource（显式 JNDI 名 +
    shareable=false + 无 name 时 name() 为空串〔默认名推导属容器职责〕+ 注入
    生效）、@PostConstruct/@PreDestroy 生命周期回调、@Priority(200) 元数据。
- 先例核对：@Resource 无 name 时注解 API 返回空串（非字段名）——默认名推导是
  容器行为（ Jakarta Annotations 2.1 §2.3），首版误断言为字段名已修正。
- 计数口径：test_package/MANIFEST.yml assertion_count 76 = 75（原）+ 1
  （HarmonyOS 专项逻辑测试）；manifest.yaml adapted_test_pass_rate 71/71 =
  53 探针 + 17 E2E + 1 专项。

## 本地预检（真机 HarmonyOS PC aarch64 + bishengjdk 17.0.13）
- 全量试跑：`mvn -f api/pom.xml clean package -B -DskipTests=false` → BUILD SUCCESS
  （54.7s），surefire No tests to run；三 jar 产物齐全。
- test_package 探针与消费者用例：用试跑产出的 jar，`javac -encoding UTF-8` 编译 +
  java 运行，**53/53 反射断言 + 17/17 E2E 全过（rc=0）**（2026-10-08）。
- 负向对照（同 validation-api 口径可复现）：仅 JDK classpath（无 API jar）时
  编译失败——探针 import 16 个 jakarta.annotation 类型，非空转。

## 真机验证（HarmonyOS PC aarch64，2026-10-08 通过）

- **conan create 全流程 PASS**（构建 + 打包 + test_package 一体）：
  `conan create archives/j/jakarta-annotation-api/2.1.1 -pr:h=ci/conan/profiles/ohos-aarch64
  -pr:b=ci/conan/profiles/ohos-aarch64` → exit 0。
- **构建**：真机 bishengjdk 17.0.13 + 配方自取 Maven 3.9.11（缓存命中
  ~/apache-maven-3.9.11），Aliyun 镜像路由生效（日志 aliyun-central 拉取父 POM
  org.eclipse.ee4j:project:1.0.7 + enforcer + 插件），`mvn -f api/pom.xml clean
  package -B -DskipTests=false` BUILD SUCCESS，surefire: No tests to run。
- **产物**：package() 打包 1 jar（jakarta.annotation-api-2.1.1.jar）+ LICENSE.md +
  NOTICE.md → libexec/ 与 licenses/（包目录结构实证）。
- **test_package**：`test.sh` 真机执行 —— JAR 存在性 OK；javac 双文件编译通过；
  探针 `PASS: jakarta.annotation probe - 53 assertions`；
  消费者 `E2E TEST SUMMARY: 17 passed, 0 failed` + `PASS: jakarta.annotation
  consumer E2E - real annotation-driven container flow`。
- **git diff --check**：干净（无空白错误）。

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
- @ManagedBean 在 2.1.1 标记 @Deprecated(forRemoval)（下个大版本将移除），探针
  断言该状态以防下游消费者误用
