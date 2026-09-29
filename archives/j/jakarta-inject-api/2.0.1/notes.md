# jakarta-inject-api 2.0.1 — 适配笔记

## 概述
Jakarta Dependency Injection 是 JSR-330 标准 API（jakarta.inject 包），提供 @Inject/@Named/@Provider/@Qualifier/@Scope/@Singleton 等注解。纯 Java API 库，无实现，需要 JVM 运行环境（bishengjdk 17）。
本 PR 采用源码编译方式，使用 Maven 构建。

## 构建方式
- 类型：源码编译（Maven）
- 来源：GitHub tarball (https://github.com/jakartaee/inject/archive/refs/tags/2.0.1.tar.gz)
- SHA256: 51df7e4b118f67f37eb55128dfe475a55b702581609987b06908d744bc5ee33c
- 构建工具：Maven 3.9.11（上游无 mvnw wrapper，配方自取二进制并 sha256 校验）
- Java: bishengjdk 17.0.13
- 许可证: Apache-2.0

## 补丁
### inject-0001-jdk17-bundle-doclint.patch（JDK 17.0.13+ 构建兼容）
1. maven-bundle-plugin 4.2.1 在 JDK 17.0.13+ 上抛 ConcurrentModificationException（旧版 bnd 与新版 JDK ZipFile 实现不兼容）→ 升级 5.1.9
2. maven-javadoc-plugin doclint 在 JDK 17.0.13+ 对 javadoc 注释标题层级（\<h3> 紧跟 \<h1>）报错 → 配置 doclint:none

## 上游测试
- 上游无测试源码（API-only 模块，tarball 无 src/test 目录），0 个测试
- 构建命令：mvn clean package -B -DskipTests=false（package 阶段编译主源码 + javadoc + sources + jar）

## test_package 测试
test_package 通过 Java 反射验证 jakarta.inject API 功能（在鸿蒙真机上运行）：
1. 编写 TestJakartaInject.java，反射加载 @Inject/@Named/@Provider/@Qualifier/@Scope/@Singleton 六类注解，并断言核心契约（@Inject 为注解类型、Provider.get() 返回 Object）
2. test.sh 使用 javac 编译测试程序，java 运行验证
3. 11 个断言：JAR 存在性、编译、8 个 API 断言、PASS 输出

## 注意事项
- 纯 Java API 库，需要 JVM 运行环境（bishengjdk 17）
- 构建需要网络（Maven 下载依赖与插件、配方自取 Maven 二进制）
- JAR 存放在 libexec/ 目录，通过 cpp_info.libdirs 导出
- JAVA_HOME 优先取环境变量，其次检测常见 JDK 路径，缺失时经 cmd-pkgs 自动安装
