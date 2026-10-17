# weupnp 0.1.4 适配笔记

## 编译环境

- 构建系统: maven（上游 `pom.xml`，`packaging=bundle` → OSGi bundle JAR）
- 编译日期: 2026-10-01
- 平台 / JVM: OpenHarmony（`os.name=harmonyos`, `os.arch=aarch64`）+ BiSheng JDK 17.0.13
- 构建工具: Apache Maven 3.6.3（官方归档，SHA-256 锁定）
- 状态: built
- 语言: **Java（JVM）**，无 C/C++ 源文件、无 JNI；`lang-preflight` 判定 `detected_language=java`

## 源码与身份核验

```bash
$ curl -sSL -o weupnp-0.1.4.tar.gz \
    https://github.com/bitletorg/weupnp/archive/refs/tags/weupnp-0.1.4.tar.gz
$ sha256sum weupnp-0.1.4.tar.gz
32f80e4249272c1809fd5e4e505a5e67af9600bb72b7993d1cea0a2c9515c333   # rc=0
$ grep -A2 Checksums-Sha256 weupnp_0.1.4-3.dsc   # deb.debian.org pool
 32f80e4249272c1809fd5e4e505a5e67af9600bb72b7993d1cea0a2c9515c333 22496 weupnp_0.1.4.orig.tar.gz
```

GitHub 官方 tag 归档与 Debian `orig.tar.gz` **逐字节一致**（22496 B），源码身份成立。
上游 tag 全名为 `weupnp-0.1.4`（`0.1.4` 会 404）。

## 编译步骤

```bash
# 1) 预置 JDK（worker 无 JDK 时由配方自动执行）
$ sh ~/.install-jdk.sh 17.0.13                     # cmd-pkgs，SHA-256 锁定
# 2) 预置 Maven（官方归档，SHA-256 锁定）
#    配方内以 conan get() 解压到 <build_folder>/_tools/maven
# 3) 真实构建（源码树 = 解压后的上游 tarball + patches/0001）
$ JAVA_HOME=~/bishengjdk17 PATH=$JAVA_HOME/bin:$PATH \
  sh <maven>/bin/mvn clean package -B -DskipTests=false
[INFO] No tests to run.
[INFO] BUILD SUCCESS
EXIT_CODE=0   elapsed=45s（本地热缓存）
```

产物：`target/weupnp-0.1.4.jar`（30372 B），包内 7 个 `.class`（6 个公共类 + 1 个内部类
`GatewayDiscover$SendDiscoveryThread`）、`license.txt` 与 OSGi MANIFEST（`Bundle-SymbolicName:
org.bitlet.weupnp`、`Export-Package`、`Import-Package: javax.xml.parsers,org.xml.sax,org.xml.sax.helpers`、
`Main-Class: org.bitlet.weupnp.Main`）。所有 class 字节码 major=52（Java 8）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `[ERROR] Source option 5 is no longer supported. Use 7 or later.` / `Target option 5 …`（EXIT_CODE=1，335s） | 上游 `pom.xml` 的 `maven-compiler-plugin` **硬编码** `<source>1.5</source><target>1.5</target>`（weupnp 为 2015 年产物）；JDK 17 已删除 source/target < 7 的支持 | `patches/0001-pom.xml.patch` 将 1.5 → 8（+2/-2） |
| 2 | 追加 `-Dmaven.compiler.source=8 -Dmaven.compiler.target=8` 无效（EXIT_CODE=1，4s，同一条报错） | 这两个值写在插件 `<configuration>` 里，属**显式配置**，优先级高于 `${maven.compiler.source}` 属性默认值，命令行无法覆盖；`maven-compiler-plugin:3.1` 也不支持 `release` 参数 | 放弃命令行覆盖，改为打补丁（即问题 1 的方案） |
| 3 | `ERROR: Package type is 'library', but no 'shared' option declared` | Conan 2 校验：`package_type="library"` 必须声明 `shared` 选项；Java 制品没有 shared/static 语义 | `package_type = "unknown"`（显式声明无 C/C++ 二进制语义，与 `archives/j/jackson-jr` 一致），不再需要假 `shared` 开关 |
| 4 | OHOS worker 无 JDK、无 Maven（`conan download maven/3.9.6` rc=1；cmd-pkgs 无 `install-maven.sh` 404；上游无 `mvnw`） | 构建工具不在制品仓，也不在系统镜像内 | JDK 走 cmd-pkgs 安装脚本（SHA-256 锁定）；Maven 走官方 `archive.apache.org` 归档 + conan `get()`（同 `archives/j/jflex` 策略） |

> 问题 2 是一次**已排除方向**的正向记录：命令行覆盖路线被实测证伪后，才落到补丁路线。

## 源码修改

`patches/0001-pom.xml.patch`（唯一的源码改动，+2/-2）：

```diff
-                    <source>1.5</source>
-                    <target>1.5</target>
+                    <source>8</source>
+                    <target>8</target>
```

补丁只改构建文件的编译级别，不触碰任何 `.java` 源码，不含平台宏 / 无平台守卫。

## 依赖版本

**零第三方依赖。** 依据：

- `pom.xml` 全文无 `<dependencies>` 段（`grep -n "dependencies\|<dependency>" pom.xml` 命中 0 行）；
- 6 个 `.java` 的 import 去重后仅有 `java.io/java.net/java.text/java.util`（JDK `java.base`）、
  `javax.xml.parsers`（JDK 内置 JAXP）、`org.xml.sax(.helpers)`（JDK 内置 SAX）；
- `grep -rn "System.loadLibrary\|Class.forName\|ServiceLoader" src/` → 0（无 JNI / 服务加载）。

因此 **R36 依赖前置条件空集成立**，不需要任何 `requires()`。
构建期工具（父 POM `org.sonatype.oss:oss-parent:7`、`maven-compiler-plugin:3.1`、
`maven-resources-plugin:2.6`、`maven-jar-plugin:2.4`、`org.apache.felix:maven-bundle-plugin:2.5.4`）
不是库依赖，由 Maven 自行解析。

## 验证结果

```bash
$ python3 scripts/ohc-run.py conan-verify weupnp 0.1.4
G1: PASS  G2: PASS（conan create）G3: PASS  G4: PASS  L2/L4/L5: PASS（无 ELF cache 路径，跳过）
✅ 配方验证通过: weupnp 0.1.4
EXIT_CODE=0   elapsed=1197s
```

`conan create` 内嵌 test_package 实测（`reports/conan-create.log`）：

```
weupnp/0.1.4@ohpcd/stable: Apply patch (portability): Raise maven-compiler-plugin source/target …
weupnp/0.1.4@ohpcd/stable: JDK found at /storage/Users/currentUser/bishengjdk17
weupnp/0.1.4@ohpcd/stable: package(): Packaged 1 '.jar' file: weupnp-0.1.4.jar
HMBS_UPSTREAM_TEST_RESULT={"status": "passed", … "discovered": 0, "note": "upstream_ships_no_automated_tests"}
======== Launching test_package ========
weupnp/0.1.4@ohpcd/stable (test package): Running test()
total=23 passed=23 failed=0 skipped=0 ohos_cases=3 ohos_passed=3 exit=0
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "discovered": 23, "passedCount": 23, "ohosCases": 3, "ohosPassed": 3, …}
```

## 上游测试

**上游 0.1.4 没有任何自动化测试入口**（清点证据见 `reports/upstream-verification.md`）：
无 `src/test/`、无 JUnit/TestNG 依赖、`pom.xml` 无 test/surefire 插件、无 CI 配置、无 wrapper。
上游构建自身即给出结论：`[INFO] No tests to run.`

唯一可运行的上游样例是包内 demo 入口 `org.bitlet.weupnp.Main`：

```
$ java -jar target/weupnp-0.1.4.jar
3:12:56 PM: Starting weupnp
3:12:56 PM: Looking for Gateway Devices...
3:13:05 PM: No gateways found
3:13:05 PM: Stopping weupnp
EXIT_CODE=0   elapsed=9s
```

该入口同时被 test_package 用例 `Upstream_Main_entrypoint` 覆盖。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `libexec/weupnp-0.1.4.jar` | 30372 B | OSGi bundle JAR（`Bundle-SymbolicName: org.bitlet.weupnp`） |
| `licenses/license.txt` | 503 行 | 上游 LGPL-2.1 许可证文本 |

包内只安装 `libexec/`（JAR）与 `licenses/`；`package_info()` 暴露 `WEUPNP_JAR` / `WEUPNP_VERSION`
（build + run env）。纯库包，无 `bindirs`，因此按 R38 不需要 `commands.json`。

## 注意事项

1. **构建期需要外网**：`archive.apache.org`（Maven 分发）+ `repo.maven.apache.org`（插件与父 POM）。
   实测 `archive.apache.org` 从 OHOS worker 下载 9.5 MB 耗时约 9.4 分钟，CI 需预留足够构建预算。
2. Maven 分发解压在 `build_folder/_tools/maven` 下，不写入任何共享前缀（不污染 `$HOME/usr/local`）。
3. 补丁只改 `pom.xml`，若上游将来发布已修正编译级别的新版本，需同步复核该补丁是否仍适用。
4. `java -jar` 可用是因为上游在 `maven-jar-plugin` 中设置了 `Main-Class`；本包按**库**分类打包
   （无 `bindirs`、无 `commands.json`），`Main` 只作为 demo/样例入口。
5. **JDK 自动安装分支的验证边界（如实声明）**：`_find_or_install_java()` 只有在找不到 JDK 时才会走
   「`download()` 取 cmd-pkgs `install-jdk.sh` → `sh` 执行」这条分支。本机已预装
   `~/bishengjdk17`（`java.vendor=bisheng`），因此 **conan create / W3 中该分支走的是 early-return，
   未被端到端执行**；该分支的 `download()` 机制已用隔离配方单独实测（sha256 校验生效，
   落盘 `install-jdk.sh` 2475 B）。后续若有干净 worker，应在无预装 JDK 环境补验一次。
6. **JAR 非字节可复现**：`maven-jar-plugin` 会把构建时间戳写入条目，同一源码多次构建的 JAR
   字节数与 sha256 会略有差异（实测 30370~30373 B）。校验 JAR 身份时应以「类清单 + 字节码版本
   major=52 + OSGi 头」为准，`manifest.yaml` 中记录的 `artifact_sha256` 仅为**本次**构建产物指纹。
---

**编译结束**: 2026-10-01 17:11
**最终状态**: built
