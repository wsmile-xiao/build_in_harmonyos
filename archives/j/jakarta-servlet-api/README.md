# jakarta-servlet-api 6.1.0

## 软件描述
Jakarta Servlet 6.1 是 Java Web 容器的核心 API 规范（Jakarta EE 11 组成部分），提供 Servlet/Filter 生命周期契约、HTTP 请求响应抽象、Cookie 与 Session 管理、异步处理（AsyncContext）与 multipart 上传（Part）。

## 功能概述
- **servlet 契约**：`jakarta.servlet.Servlet` / `ServletConfig` / `ServletContext` / `GenericServlet`
- **Filter 链**：`Filter` / `FilterChain` / `FilterConfig`
- **请求响应**：`ServletRequest`/`ServletResponse` 与其 HTTP 变体、`ServletInputStream`/`ServletOutputStream`
- **HTTP 语义**：`Cookie`、`HttpSession`、`Part`（multipart）、`HttpServlet`（TRACE/HEAD 等）
- **异步与派发**：`AsyncContext`、`RequestDispatcher`、`DispatcherType`（REQUEST/FORWARD/INCLUDE/ERROR/ASYNC）

## OHOS 适配

### 构建方式
- **纯 Java API**（无 native 代码）：GitHub tarball 源码 + Maven 编译 `api` 模块，产出单个 JAR 入 `libexec/`（同 `jakarta-cdi-api` 4.0.1 / `jakarta-inject-api` 2.0.1 的既有范式）
- **只构建 api 模块**（`mvn -pl api -am`）：根 pom 的 modules 含 `api`/`spec`/`tck`——`spec` 是文档模块、`tck` 是完整 Servlet TCK（独立大工程），都不是 API 制品的组成部分
- **工具链自取**：上游无 mvnw——配方经 cmd-pkgs 自取 bishengjdk 17.0.13，并从 repo1.maven.org 取 apache-maven 3.9.11（sha256 钉校验）

### 关键点
1. **tag 形态**：该仓库的 release tag 带 `-RELEASE` 后缀（`6.1.0`、`v6.1.0` 均 404，`6.1.0-RELEASE` 为 200）
2. **上游测试**：`api/src/test/java` 共 10 个源文件 = 3 个 JUnit 5 测试类（CookieTest / CanonicalUriPathTest / HttpServletTest，17 个测试方法）+ 7 个 mock/辅助类；`-DskipTests=false` 时由 surefire 在 package 阶段执行
3. **`package_info()`**：`libdirs = ["libexec"]`，消费者把 JAR 加入 classpath 即可

### 与 Linux 的差异
无差异——纯 Java API（无 native、无平台相关代码），全平台一致。

## 依赖关系
- **构建期**：bishengjdk 17.0.13 + apache-maven 3.9.11（配方自取，不产生 Conan 依赖）
- **运行期**：无（API JAR，容器实现由消费者提供）

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 6.1.0 | built | 2026-10-07 | 源码编译 api 模块，单 JAR 入 libexec |

## 参考资料
- 上游仓库: https://github.com/jakartaee/servlet
- 规范页面: https://jakarta.ee/specifications/servlet/6.1/
