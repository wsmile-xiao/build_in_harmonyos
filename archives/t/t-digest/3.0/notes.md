# t-digest 3.0 — 适配笔记

## 概述
T-Digest 是 Ted Dunning 提出的流式分位数估计算法，用极小的内存对海量数据估计中位数、P95/P99 等分位数，支持合并（map-reduce 友好）。
本 PR 采用源码编译方式，使用 Maven 构建并运行上游 JUnit 测试。

## 构建方式
- 类型：源码编译（Maven）
- 来源：GitHub tag t-digest-3.0（https://github.com/tdunning/t-digest/archive/refs/tags/t-digest-3.0.tar.gz）
- SHA256：a18185a8e12be50ee27167d915e3e7a5cc596f2b714c3bd883975367a5ed250d（2026-09-22 直连下载验证，大小 3282914）
- 构建工具：Maven 3.6.3（优先系统 mvn，缺失时从 archive.apache.org 自动下载，SHA256 已在配方中 pin）
- Java：bishengjdk 17.0.13（优先 JAVA_HOME，常见路径探测，缺失时经 cmd-pkgs 自动安装）
- 许可证：Apache-2.0
- 补丁：无补丁文件。pom 调整由 conanfile._patch_pom() 在 build() 内以子串替换就地完成（JDK 编译级别 1.6/1.7→1.8；Surefire parallel methods→none 并去掉 perCoreThreadCount/threadCount）。上一轮两个 context 补丁因缩进与 Conan 严格打补丁器（fuzz=0）不兼容报"source file is different - pom.xml"，故改走程序化路线
- 上游 surefire 串行原因：上游配 parallel=methods + perCoreThreadCount，多核下多线程并发调用 RandomUtils.useTestSeed 共享 MersenneTwister，偶发 ArrayIndexOutOfBoundsException Index 624；改为 parallel=none 串行执行，不删减任何用例与断言

## 上游测试
- 测试框架：JUnit 4.8.2（junit 4.8.2，经 maven-surefire-plugin 2.16 运行）
- 测试文件数：6 个 *Test.java（含 AVLGroupTreeTest 5、AVLTreeDigestTest 19、ArrayDigestTest 21、GroupTreeTest 6、IntAVLTreeTest 2、TreeDigestTest 19）
- 测试方法数：72 个 @Test 方法（grep -r @Test 统计；TDigestTest.java 为基类无 @Test，2 个 Benchmark 不计）
- 运行命令：mvn clean package -B -DskipTests=false -Dmaven.javadoc.skip=true（package 阶段含 test，运行上游测试并产出 target/t-digest-3.0.jar；javadoc skip 仅跳过 API 文档，原因见下）
- 运行位置：build() 方法中（CI Worker / 真机）
- javadoc 说明：上游 pom 把 maven-javadoc-plugin 绑定到 package 阶段，JDK17 严格 doclint 把 61 个历史缺注释警告升级为 27 个 error（`27 errors / 61 warnings / Command line was: .../bin/javadoc`），在 Surefire 运行前直接让构建失败。加 `-Dmaven.javadoc.skip=true` 只跳过文档生成，不影响编译与测试口径
- 计数口径：解析 target/surefire-reports/TEST-*.xml 的 tests/failures/errors/skipped 属性求和，不做字符串数数与减法推导；恒等式 passed + failed == executed、executed + skipped <= discovered 在代码中由同一数据源计算保证

### 测试目录结构
src/test/java/com/tdunning/math/stats/ 下包含：
- AVLGroupTreeTest.java、AVLTreeDigestTest.java、ArrayDigestTest.java
- GroupTreeTest.java、IntAVLTreeTest.java、TreeDigestTest.java
- TDigestTest.java（公共基类，无 @Test）、QuantileEstimator.java（辅助类）
- TDigestBenchmark.java、TDigestMemoryBenchmark.java（Caliper 基准，非 Surefire 用例）

## test_package 测试
test_package 通过 Java API 调用验证 t-digest 功能（在鸿蒙真机上运行）：
1. 编写 TestTDigest.java，覆盖 ArrayDigest/TreeDigest/AVLTreeDigest 的 create/add/quantile/cdf/size/centroidCount/compress/merge/序列化与 NaN 拒绝，共 14 个断言
2. test.sh 使用 javac 编译测试程序，java 运行验证 API 调用，统计 PASS/FAIL 并输出 HMBS_TEST_PACKAGE_RESULT
3. conanfile.py 负责找 JDK、定位 libexec/t-digest-3.0.jar、调用 test.sh

## 注意事项
- t-digest 是纯 Java 库，需要 JVM 运行环境（bishengjdk 17）
- 上游 pom 指定 source/target 1.6，JDK17 直接报错，必须先打补丁到 1.8 才能编译
- Maven 首次运行需下载依赖（junit、mahout-math、stream、caliper、java-sizeof、guava），需网络连接
- JAR 存放在 libexec/ 目录，通过 buildenv TDIGEST_JAR 导出给消费者
- JAVA_HOME 优先取环境变量，其次检测常见 JDK 路径（bishengjdk17、openjdk-17 等），缺失时经 cmd-pkgs 清晰安装而非静默失败
- 参考实现：archives/j/jflex/1.9.1（Maven + Surefire XML 解析 + HMBS 双标记模式）
