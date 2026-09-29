# draft-jakarta-inject-2.0.1-jar-api-maven-src-compile-jvm-runtime

## 症状

jar-library 类任务（如 jakarta-inject-api 2.0.1）在 OHOS 上适配时遇到两类问题：

```
# 问题一：上游 repo 没有 mvnw wrapper
./mvnw: No such file or directory

# 问题二：OHOS 设备无系统级 JDK
JAVA_HOME not set and no JDK found in common locations
```

## 根因

1. 纯 Java API 发行物（JSR-330 等 spec API）只发布官网 jar + GitHub 源码 tarball，
   上游 repo 不含 mvnw wrapper（Maven 工程规范但未带 wrapper），构建期 Maven 依赖
   无法满足。
2. OHOS 设备（真机）无系统级 JVM；鸿蒙 PC 生态用 bishengjdk 17 提供 Java 运行时，
   构建期（CI worker）与 test_package 期（真机）都必须自行解析 JAVA_HOME。
3. 易错点：直接打包官网预编译 jar 做数据包——违反 L1c（必须源码编译），且无上游
   测试执行记录。

## 修复

conanfile.py 采用 jar-library 范式（与已合入的 jackson-core 2.14.1 同族）：

```python
# ① Maven 自取（上游无 mvnw 时）：repo1.maven.org 二进制 + sha256 校验
MAVEN_SHA256 = "4b7195b6a4f5c81af4c0212677a32ee8143643401bc6e1e8412e6b06ea82beac"
# 解压至 ~/apache-maven-3.9.11，build() 内 PATH 前置 mvn bin

# ② JVM 探测链：JAVA_HOME → ~/bishengjdk17 → PATH java → cmd-pkgs 自动安装
#    curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install-jdk.sh | sh -s -- 17.0.13

# ③ build(): bash -c "cd {source_folder} && mvn clean package -B -DskipTests=false"
#    产物：target/jakarta.inject-api-2.0.1.jar

# ④ package(): jar → libexec/；LICENSE*/NOTICE* → licenses/
# ⑤ package_info(): self.cpp_info.libdirs = ["libexec"]

# ⑥ settings = "os", "arch"（纯 Java 无交叉编译器）；validate() 限定 os in (Linux, OHOS)
# ⑦ R38 库包：无需 commands.json
```

test_package 用 javac+java 编译运行消费者程序，反射断言 API 类可加载；
test.sh 的 JAVA_HOME 候选列表必须含真机路径
`/storage/Users/currentUser/usr/local/bishengjdk17`。

## 验证

- jakarta-inject-api 2.0.1 本地 Maven 构建干净（上游 0 测试，API-only 模块无 src/test）
- 真机 test_package 编译运行 PASS（11 断言：1 JAR + 1 编译 + 8 反射断言 + 1 PASS）
- CI /rebuild 门禁全绿

## 经验

- 判断"是否源码编译"看官网 jar 是否伴随源码 tarball：有源码就必须走 Maven 编译，
  数据包打包原 jar 仅限无源码的纯数据发行物。
- Maven 二进制自取比依赖系统包管理器可靠（sha256 锁定 + ~ 下缓存复用）。
- 构建期与测试期的 JAVA_HOME 解析要各自独立实现（conanfile.py 与 test.sh 环境不同）。
