# jakarta-authentication-api 3.0.0 — 适配笔记

## 概述
Jakarta Authentication 定义认证机制的通用底层 SPI（jakarta.security.auth.message 包），
描述调用者凭证的获取/校验/身份传递契约（ServerAuthContext / ServerAuthModule /
AuthConfigProvider 等）。纯 Java API 库，无实现，需要 JVM 运行环境（bishengjdk 17）。
本 PR 采用源码编译方式，使用 Maven 构建。

## 构建方式
- 类型：源码编译（Maven）
- 来源：GitHub tarball (https://github.com/jakartaee/authentication/archive/refs/tags/3.0.0-RELEASE.tar.gz)
- SHA256: 847989c565848f493f9a9dc97809778ad68352a34a5db5a33e1b4f1e11f66bf3
- 构建工具：Maven 3.9.11（上游无 mvnw wrapper，配方自取二进制并 sha256 校验）
- Java: bishengjdk 17.0.13
- 许可证: EPL-2.0（根目录 LICENSE.md；NOTICE.md 一并分发到 licenses/）
- 模块结构：根 pom 是 authentication-parent 聚合器，API 模块在 api/（父
  ee4j:project:1.0.6）；构建只跑 api 模块：`cd api && mvn clean package -B`

## 补丁
无。本机已验证干净构建（JDK17 + Maven 3.9.11，api 模块零告警，产物 45346 字节）。
官网原 jar sha256 仅作参考——配方必须从源码编译，不打包原 jar。

## 上游测试
- 上游无测试源码（API-only 模块，api/src 无 test 目录），0 个测试
- 构建命令：mvn clean package -B -DskipTests=false（package 阶段编译主源码
  24 个 .java + module-info.java，生成 jar + javadoc + sources）

## test_package 测试
test_package 通过 Java 反射断言 + E2E 消费者测试验证 jakarta.security.auth.message API 功能（在鸿蒙真机上运行）：
1. TestJakartaAuthentication.java：反射加载 8 个核心接口/类
   （ServerAuthContext / ServerAuthModule / AuthConfigProvider / ClientAuthContext /
   AuthStatus / MessageInfo / MessagePolicy / CallerPrincipalCallback），
   并断言核心契约（ServerAuthModule 为接口、AuthStatus.SUCCESS 为 AuthStatus 类型常量）
2. TestAuthFlow.java：完整消费者测试（端到端）——模拟服务器容器提供并安装
   AuthConfigFactory 实现（setFactory/getFactory），注册 AuthConfigProvider，经工厂取回，
   获取 ServerAuthConfig（消息层/保护性契约）→ ServerAuthContext → validateRequest →
   AuthStatus.SUCCESS → 容器侧 CallbackHandler 按 JSR-196 契约处理 CallerPrincipalCallback
   把调用者身份写入 clientSubject → secureResponse/cleanSubject 生命周期收尾 →
   removeRegistration 注销。10 个测试用例（E2E-1..E2E-10），每例独立 TEST PASS/FAIL
   判定 + E2E TEST SUMMARY 汇总，任一失败进程退出码 1，纯 API jar 运行无第三方依赖
3. test.sh 使用 javac 编译测试程序，java 运行验证
4. 23 个检查项：JAR 存在性、编译、10 个反射/契约断言、10 个 E2E 测试用例、汇总输出

## 注意事项
- L0p 门禁（CI）要求 settings 四项 os/compiler/build_type/arch，纯 Java 包同样补全声明（仅过门禁，不影响构建逻辑；leaflet-markercluster/laptop-detect 同款）
- 纯 Java API 库，需要 JVM 运行环境（bishengjdk 17）
- 构建需要网络（Maven 下载依赖与插件、配方自取 Maven 二进制）
- JAR 存放在 libexec/ 目录，通过 cpp_info.libdirs 导出
- JAVA_HOME 优先取环境变量，其次检测常见 JDK 路径，缺失时经 cmd-pkgs 自动安装
- Maven Central 直连在 CI 环境会 Connection reset（CI #63603：maven-bundle-plugin jar
  下载中断，前 20 个插件正常）→ build() 写入 maven-settings.xml 把 central 路由到
  阿里云镜像（maven.aliyun.com/repository/central，中国CDN）+ 3 次重试（间隔 20s）+
  直连兜底；本机镜像构建实测 50s BUILD SUCCESS（对比直连 6min+ 且不稳定）

## 真机复验（2026-09-27）
- 平台：HarmonyOS PC（aarch64），profile `ci/conan/profiles/ohos-aarch64`，conan 2.29.1
- 引用：`jakarta-authentication-api/3.0.0@ohpcd/stable`，构建 `--build=missing`
- 官方 conan-verify 全绿：G0 预构建评估 / G1 配方完整性 / G2 conan create 干净构建 /
  G3 系统同名库隔离（R26）/ G4 产物完整性 全部 PASS；L2/L4/L5 跳过（纯 JAR 包无 cache 路径），
  终态 verdict **PASS**、VERIFY_EXIT=0、可标记 published（报告随档 `reports/conan-verify-report.md`）
- test_package 23 项检查在真机全部通过：JAR 存在性、javac 编译、8 类反射加载
  （ServerAuthContext / ServerAuthModule / AuthConfigProvider / ClientAuthContext /
  AuthStatus / MessageInfo / MessagePolicy / CallerPrincipalCallback）、2 项 SPI 契约断言
  （ServerAuthModule 为接口、AuthStatus.SUCCESS 类型常量）、10 个 E2E 测试用例
  （工厂安装→注册→取回→config→context→validateRequest→SUCCESS→身份注入→生命周期→注销，
  每例 TEST PASS + E2E TEST SUMMARY 10 passed 0 failed）、
  汇总输出（日志随档 `reports/conan-create.log`）
- 真机侧 conandata 源码 URL 临时换本地镜像 `http://192.168.43.12:8137/`（E017 网络受限绕过），
  提交版本为官方 GitHub URL，sha256 相同

## 真机复验·第二轮（2026-09-28，CI #63603 修复后）
- 配方修订：build() 增加阿里云 central 镜像 + 3 次重试 + 直连兜底（见「注意事项」），
  新配方修订版在真机强制重建（`--build=jakarta-authentication-api/*`）：
  构建目录 19:37-19:40 全新生成，`maven-settings.xml` 镜像配置落盘佐证新 build() 实跑
- test_package 23 检查项全过（10 反射/契约 + 10 E2E 测试用例 + JAR + 编译 + 汇总，
  E2E TEST SUMMARY 10 passed 0 failed）
- 官方 conan-verify 复跑全绿：G0-G4 全 PASS、L2/L4/L5 跳过、终态 Verdict PASS /
  可标记 published（报告随档 reports/conan-verify-report.md，2026-09-28T19:41:37）
- 日志随档 reports/conan-create.log（2026-09-28 新配方版）
