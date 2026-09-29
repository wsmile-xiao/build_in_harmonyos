# jakarta-cdi-api 4.0.1 — 适配笔记

## 概述
Jakarta Contexts and Dependency Injection（CDI）4.0 标准 API。上游 reactor 三个模块：
- **spec**：pom-only 文档模块（无构建产物）
- **lang-model**：语言模型 API jar（jakarta.enterprise.lang.model.*）
- **api**：CDI API jar（jakarta.enterprise.context/inject/event/util/spi 等）

纯 Java API 库（无实现），需要 JVM 运行环境（bishengjdk 17）。本 PR 采用源码编译方式，使用 Maven 构建。

## 构建方式
- 类型：源码编译（Maven reactor，根目录一次 `mvn clean package -B -DskipTests=false`）
- 来源：GitHub tarball (https://github.com/jakartaee/cdi/archive/refs/tags/4.0.1.tar.gz)
- SHA256: 5f213212ee8839036915f4fd66578421f6ea181aa7f62d1c34bcb942edba02a6
- 构建工具：Maven 3.9.11（上游无 mvnw wrapper，配方自取二进制并 sha256 校验）
- Java: bishengjdk 17.0.13
- 许可证: Apache-2.0（根目录 LICENSE.txt / NOTICE.md → licenses/）

## 补丁
### cdi-0001-jdk17-doclint.patch（JDK 17.0.13+ 构建兼容，portability）
api/pom.xml 的 maven-javadoc-plugin 配置 `<doclint>none</doclint>`：JDK 17.0.13+
的 doclint 对 javadoc 注释标题层级（\<h3> 紧跟 \<h1>）报 heading-sequence 错误，
上游从未在这些补丁版本上构建过。
（jakarta-inject-api 还需升级 maven-bundle-plugin 解决 bnd/ZipFile 问题；
本 reactor 已 pin maven-bundle-plugin 5.1.2，无该问题，无需该改动。）

## 上游测试
- **56 个 TestNG 方法，全部在 api 模块**（33 个 test 源文件 / 12 个测试类）；
  lang-model 与 spec 模块无测试源码。
- 源码证据：api/target/surefire-reports/junitreports/TEST-*.xml 共 12 份，
  tests 求和 = 56，failures=0 / errors=0 / skipped=0。
  （testng-results.xml total=5 为 Surefire 聚合套件计数，逐类 junit 报告为准。）
- 构建命令：mvn clean package -B -DskipTests=false（package 阶段编译主源码 +
  javadoc + sources + jar，并运行上述 56 个测试）
- 口径订正：任务卡写"51 lang-model + 5 api"，与 surefire 记录不符（实测 56 个
  全在 api 模块），本配方按实测口径记录。

## 产物
- `api/target/jakarta.enterprise.cdi-api-4.0.1.jar` → `libexec/`
- `lang-model/target/jakarta.enterprise.lang-model-4.0.1.jar` → `libexec/`
- api 模块依赖 lang-model（同一 reactor 内），**消费者需两个 jar 同时在 classpath**。
- cdi-api jar **不内嵌** jakarta.inject / interceptor / annotation / el 类（zip 清单
  核对：仅 jakarta/enterprise/*，214 条目；lang-model jar 38 条目）；需要这些 API 的
  消费者需另行提供（例如同仓 jakarta-inject-api 包）。

## test_package 测试
- `TestJakartaCdi.java`：纯反射断言（只用 JDK 类型，编译期不依赖被测 jar），19 项：
  - 1-11 类型加载：RequestScoped / ApplicationScoped / SessionScoped / Dependent /
    NormalScope / Event / AnnotationLiteral / lang.model.AnnotationInfo /
    lang.model.declarations.ClassInfo / lang.model.types.Type / AnnotationTarget
  - 12 RequestScoped 是注解类型
  - 13-15 三个作用域注解携带 @NormalScope 元注解；SessionScoped 为
    `@NormalScope(passivating=true)`（读取注解元素实际值，钝化契约）
  - 16 @NormalScope 的 @Target 恰为 ANNOTATION_TYPE
  - 17 Event 有 3 个 select() 重载（程序化事件触发契约）
  - 18 AnnotationLiteral 实现 java.lang.annotation.Annotation
  - 19 lang.model.types.Type 是接口且继承 AnnotationTarget
- `test.sh`：2 个 jar 存在性 + javac（`-encoding UTF-8`）编译 + java 运行 + PASS 校验。
- 断言总数 **79** = 上游 56 + test_package 23（2 jar + 1 编译 + 19 反射 + 1 PASS）。
- **设计说明**：探针只做「两个 jar + JDK」范围内可解析的断言。cdi-api 的
  Instance / CDI 等类型继承 jakarta.inject.Provider 等外部 API，两 jar classpath
  上无法解析其超接口，故不对其做 getInterfaces/getMethod 类断言（避免
  NoClassDefFoundError 假阴性）——已实测验证该边界。

## 本地预检（Windows + JDK 17.0.17，非真机）
用 jar-src 本地构建产出的两个 jar，仅将两 jar 放上 classpath：
- `javac -encoding UTF-8` 编译通过；
- `java -cp <api.jar>:<lang-model.jar>:<tmp>` 运行输出 OK[1]-OK[19] 全过 + PASS 行，exit 0（19/19）；
- 负向对照：仅 api.jar 上 classpath 时在第 8 项（lang-model 类加载）准时失败 exit 1，证明探针非空转。
- `test.sh` 全流程演练：本地复制一份、仅把 Windows 需要的两处 `-cp` 分隔符换成 `;` 后运行，
  2 个 jar 检查 + javac + java + PASS 校验全绿 `exit 0`（脚本体保持 POSIX `:` 分隔符，真机 Linux 正确）。
- 补丁核验：`git apply --check -R -p1` 通过（补丁与本地构建所用状态精确一致）；
  与 jar-src 源文件 md5 相同（677f5a278884165f33cac0b9b269b5c5）。
## 真机验证（HarmonyOS PC aarch64，2026-09-27）
`python3 scripts/ohc-run.py conan-verify jakarta-cdi-api 4.0.1` → **Verdict PASS**（exit 0）。
- G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS，结论「可标记 status: published」，R46 result.json 已上报（draft:false）。
- 真机构建：reactor 四模块全 SUCCESS（cdi-parent 13.9s / spec-doc 5:13 / lang-model 5:24 / api 3:06）；
  上游 56 个 TestNG 真机构建时执行全过（surefire 汇总 Tests run: 51+5=56，0 失败/0 错误/0 跳过）。
- 消费者探针：2 JAR 存在 + javac 编译 + 19 反射断言 + PASS 全过（=== All tests passed ===）。
- 报告落档 `reports/conan-verify-report.md`（Verdict PASS，2026-09-27T13:45）。

### 真机修复记录（每一条都是设备实测踩出来的）
1. **源码下载**：ghfast.top 注入镜像读超时（ReadTimeoutError 30s×2）→ 设备侧临时把
   conandata 源指向本机 `http.server` 镜像（sha256 不变）完成验证；提交配方保持官方 URL（R39）。
2. **Maven 自取**：OHOS 无 curl（Error 127）、python3 无 CA bundle（CERTIFICATE_VERIFY_FAILED）→
   `_ensure_maven` 加 python3 urllib 免证书回退（sha256 钉校验兜底）。
3. **HMDFS 禁 shebang**：`mvn` 脚本直接执行报 `bad interpreter: Permission denied`（Error 126，
   ELF 二进制不受影响）→ build() 显式 `sh {maven_home}/bin/mvn`。
4. **spec-doc 文档模块**：asciidoctor-maven-plugin（JRuby）generate-pdf-doc 报
   concurrent-ruby gemspec ENOENT → OHOS 上 `-Dasciidoctor.skip=true` 跳过（纯文档产物不打包），
   Linux CI 仍全量构建。

## 注意事项
- 纯 Java API 库，需要 JVM 运行环境（bishengjdk 17）
- 构建需要网络（Maven 下载依赖与插件、配方自取 Maven 二进制）
- JAR 存放在 libexec/ 目录，通过 cpp_info.libdirs 导出
- JAVA_HOME 优先取环境变量，其次检测常见 JDK 路径，缺失时经 cmd-pkgs 自动安装
- settings 声明完整四项（os/compiler/build_type/arch）：Java 包不消费编译设置，
  但 CI 的 L0p 门禁要求 OHOS profile 四项齐全（缺 compiler/build_type 直接判失败），
  四项只进 package_id，build() 不读
