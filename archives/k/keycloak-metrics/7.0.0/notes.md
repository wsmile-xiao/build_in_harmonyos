# keycloak-metrics 7.0.0 — 适配笔记

## 概述
keycloak-metrics（上游 aerogear/keycloak-metrics-spi）是 Keycloak 的
Prometheus 指标端点 SPI 插件：注册 EventListenerProvider（登录/注册/token
刷新等事件计数）与 RealmResourceProvider（/metrics 端点暴露文本格式指标）。
纯 Java 库，fat jar 分发（shade prometheus simpleclient 0.16.0）。

## 上游定位
- 仓库：https://github.com/aerogear/keycloak-metrics-spi
- tag：**7.0.0（无 v 前缀）**——codeload 200 OK 验证，commit 0331363
- 任务卡名 keycloak-metrics/7.0.0 即上游 tag 7.0.0
- 注意：上游 gradle.properties 固定 `version=6.0.1-SNAPSHOT`（上游发布习惯，
  tag 才是 7.0.0），产物 jar 名为 keycloak-metrics-spi-6.0.1-SNAPSHOT.jar

## 构建方式
- 类型：源码编译（Gradle 8.5 wrapper）
- 来源：GitHub tarball (refs/tags/7.0.0)
- SHA256: f366dd1e0f2b68e0f484c7e5917de7252560a7abc5925c2ac656f49be68fc9be
- Java: bishengjdk 17.0.13（pom 声明 21，但代码无 Java 21 特性，
  gradle 路径 sourceCompatibility=17，17 编译通过）
- 许可证: Apache-2.0

## 依赖链（无断链）
- keycloak-server-spi / keycloak-server-spi-private / keycloak-services
  （26.0.0）：**provided scope**——仅编译期从 Maven Central 拉取，不打进 jar。
  因此 keycloak 主体不需要在制品仓存在（非运行时依赖，插件运行时由
  Keycloak 容器提供）
- resteasy-reactive 3.8.5：provided scope（jakarta.ws.rs 注解编译期）
- prometheus simpleclient 0.16.0（common/hotspot/pushgateway）：compile
  scope，被 shade 进 fat jar（运行时零外部依赖）
- tomcat-servlet-api：compileOnly
- 全部从 Maven Central 在线拉取（java 直连 repo1.maven.org 验证 200）

## 上游测试
- 测试框架：JUnit 4.13 + Mockito 5.4 + system-stubs-junit4 2.0.2
- 测试类：2 个（PrometheusExporterTest 24 + MetricsFilterTest 2）
- 测试方法：26 个 @Test
- 运行命令：gradle test（与上游 Jenkinsfile `./gradlew test` 一致）
- 运行位置：build() 方法中
- 本机实测：26/26 通过（0 失败 0 错误 0 跳过，build/test-results XML 确认）

## 鸿蒙适配要点（踩坑记录）
1. **gradlew 脚本不可直接用**：鸿蒙环境 busybox xargs 不剥引号，
   `DEFAULT_JVM_OPTS='"-Xmx64m"'` 展开后带引号传给 java 报
   `Could not find or load main class "-Xmx64m"`。绕过：直接
   `java -cp gradle/wrapper/gradle-wrapper.jar org.gradle.wrapper.GradleWrapperMain`
   （wrapper 语义不变，只跳过 shell 参数解析层）
2. **gradle 发行版下载**：services.gradle.org java 直连超时。方案：curl 从
   腾讯云镜像（mirrors.cloud.tencent.com/gradle/）预下载 gradle-8.5-all.zip，
   追加 `distributionUrl=file://<本地路径>` 到 wrapper properties
   （java.util.Properties 后写的 key 生效）
3. **bishengjdk17 运行时依赖**：libjvm.so 需要 libc++_shared.so。本机从
   conan 缓存 ~/.conan2/p/clang86483f2566f6b/p/lib 提供（LD_LIBRARY_PATH）
4. **CI JDK**：build() 复用 jackson-core 先例的 cmd-pkgs install-jdk.sh
   自动安装 bishengjdk 17.0.13

## test_package 测试（消费者视角，真机运行）
test.sh 解包 fat jar 验证（不依赖 Keycloak 运行时——SPI 插件的宿主是
Keycloak 服务器，部署验证超出制品仓消费者测试范畴；验证点为 jar 自身
完整性 + 可加载性）：
1. JAR 存在性
2. SPI 注册文件内容正确（EventListenerProviderFactory →
   MetricsEventListenerFactory；RealmResourceProviderFactory →
   MetricsEndpointFactory）
3. prometheus simpleclient 已 shade（CollectorRegistry.class 存在）
4. 5 个插件类字节码存在
5. JVM URLClassLoader 加载 fat jar：prometheus 类可加载 + 插件类资源可见
   （PASS 输出）
共 10 个断言；上游 26 个 @Test 在 build() 中运行。

### ⚠ SIGPIPE 竞态坑（CI #50941 实锤，通用教训）
jar 条目断言**禁止** `unzip -l | grep -q` 管道写法：grep -q 匹配后立即
退出，unzip 输出剩余大列表时收 SIGPIPE（exit 141），`set -o pipefail`
下整条管道非零 → `if ! pipeline` 以约 25% 概率随机走进 ERROR 分支，
报"not shaded / missing"——实际 jar 内容完好。本机 20 轮压测命中 5-6 次
失败，CI #50941 断言 4 命中一次。修复：`unzip -l > 清单文件` 一次性落盘，
后续全部 `grep 文件`（零管道零竞态），30 轮压测 0 失败。任何
`<producer> | grep -q` + pipefail 的组合都有同类风险。

## 与制品仓先例的关系
- 打包模式完全对齐 archives/j/jackson-core/2.14.1（Java 源码编译 →
  Maven/Gradle → JAR → libexec/ → test_package javac/java 验证）
- 同模式先例：jackson-core、servlet-api、jackson-jr、jflex、xom、
  graalvm（test_package 含 .java）、airlift-slice

## 补丁
- patches/0001-test-jvm-allow-attach-self.patch：build.gradle 增加独立的
  byteBuddyAgent configuration（net.bytebuddy:byte-buddy-agent:1.14.6，
  与 mockito-inline 5.2.0 传递依赖同版本线），test 块加
  `-javaagent:<agent.jar>` 与 `-Djdk.attach.allowAttachSelf=true`。
  原因（CI #50756/#50767 两轮实锤）：OHOS CI worker 上 JVM 动态 attach
  API 整体不可用——
  ① 外部模式：ByteBuddyAgent.installExternal fork 的辅助进程永不返回
    （线程 dump：Test worker WAITING on ProcessImpl.waitFor）；
  ② 自附加模式：VirtualMachine.attach 抛 IllegalStateException。
  两条路都死 → Mockito inline mock maker（classpath 有 mockito-inline，
  system-stubs-junit4 依赖）初始化失败 → 全部 26 个 @Test 报
  initializationError/NoClassDefFoundError。
  解法（Mockito 官方推荐）：-javaagent 在 test JVM 启动时由 premain
  注册 Instrumentation，ByteBuddyAgent.install() 检测到已装载直接短路
  返回，运行时零 attach 调用。本机 26/26 全绿。测试用例本身零修改。

## 注意事项
- keycloak-metrics 是插件（plugin），消费方是 Keycloak 服务器进程
  （providers/ 目录部署），不是链接库——cpp_info.libdirs=["libexec"]
  惯例同 jackson-core
- jar 内不含任何 keycloak 类（provided scope），无许可证污染
