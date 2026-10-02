# weupnp 0.1.4 — 源码身份与上游测试入口核验

> 日期: 2026-10-01 ｜ 平台: OpenHarmony（`os.name=harmonyos`, `kernel 1.12.0`, `aarch64`）

## 一、源码身份核验（双通道）

| 项 | 值 |
|---|---|
| 上游工程 | `bitletorg/weupnp` — "weupnp - Trivial upnp java library" |
| 上游仓库 | https://github.com/bitletorg/weupnp |
| 上游 tag | `weupnp-0.1.4`（注意：tag 全名带前缀，`0.1.4` 会 404） |
| 请求版本 | `0.1.4` = 上游真实版本 `0.1.4`（无需修正） |
| 归档 tarball | `weupnp-0.1.4.tar.gz`，22496 B，19 个 tar 条目 / 解压后 11 个文件 |

```bash
# 通道 1：GitHub 官方 tag 归档
$ curl -sSL -o weupnp-0.1.4.tar.gz \
    https://github.com/bitletorg/weupnp/archive/refs/tags/weupnp-0.1.4.tar.gz
$ sha256sum weupnp-0.1.4.tar.gz
32f80e4249272c1809fd5e4e505a5e67af9600bb72b7993d1cea0a2c9515c333   rc=0

# 通道 2：Debian pool 的 orig.tar.gz 声明（交叉核验）
$ curl -sSL -o weupnp_0.1.4-3.dsc https://deb.debian.org/debian/pool/main/w/weupnp/weupnp_0.1.4-3.dsc
$ grep -A3 Checksums-Sha256 weupnp_0.1.4-3.dsc
Checksums-Sha256:
 32f80e4249272c1809fd5e4e505a5e67af9600bb72b7993d1cea0a2c9515c333 22496 weupnp_0.1.4.orig.tar.gz
```

**两通道 sha256 逐字节一致 ⇒ 源码身份成立。**

源码树（11 文件）：

```
weupnp-0.1.4/.gitignore
weupnp-0.1.4/CONTRIBUTING.md
weupnp-0.1.4/README.md
weupnp-0.1.4/pom.xml
weupnp-0.1.4/src/main/java/org/bitlet/weupnp/GatewayDevice.java          (673 行)
weupnp-0.1.4/src/main/java/org/bitlet/weupnp/GatewayDeviceHandler.java   (187 行)
weupnp-0.1.4/src/main/java/org/bitlet/weupnp/GatewayDiscover.java        (392 行)
weupnp-0.1.4/src/main/java/org/bitlet/weupnp/Main.java                   (147 行)
weupnp-0.1.4/src/main/java/org/bitlet/weupnp/NameValueHandler.java       (142 行)
weupnp-0.1.4/src/main/java/org/bitlet/weupnp/PortMappingEntry.java       (189 行)
weupnp-0.1.4/src/main/resources/license.txt                              (503 行)
```

语言构成：`.java` 6 个（1730 行）/ `.xml` 1 个 / `.md` 2 个 / `.txt` 1 个；
**C/C++ 源文件 0 个**。R47 `lang-preflight` 判定 `detected_language=java`
（`build_system=gradle/maven`，`源文件 6 个（java:6），主体占比 100%`）。

## 二、上游测试入口清点（R51 第一步）

```bash
$ ls src/test
ls: src/test: No such file or directory

$ find . -iname "*test*" | wc -l
0

$ grep -rn -E "junit|testng|@Test|assertEquals" . | wc -l
0

$ grep -n -i -E "surefire|junit|test" pom.xml
（无输出 —— pom.xml 未声明任何测试插件）

$ grep -n "dependencies\|<dependency>" pom.xml
rc=1   （0 行 —— 无 <dependencies> 段，故也没有 JUnit/TestNG 依赖）

$ find . -name "mvnw*" -o -name "gradlew*" | wc -l
0
$ find . -name "*.yml" -o -name "*.yaml" | wc -l
0      （无 CI 配置）
```

### 结论：**上游 0.1.4 没有任何自动化测试入口。**

这一结论由上游构建系统本身再次确认 —— `mvn clean package -B -DskipTests=false` 输出：

```
[INFO] --- maven-surefire-plugin:3.6.0:test (default-test) @ weupnp ---
[INFO] No tests to run.
```

且不产生 `target/surefire-reports/`（配方据此上报
`HMBS_UPSTREAM_TEST_RESULT={"discovered": 0, …, "note": "upstream_ships_no_automated_tests"}`）。

### 唯一可运行的上游样例

| 入口 | 说明 | 实测命令与结果 |
|---|---|---|
| `org.bitlet.weupnp.Main` | 上游自带 demo：SSDP 发现 → 列出网关 → 端口映射往返 | `java -jar target/weupnp-0.1.4.jar` → `EXIT_CODE=0`，9s，输出 `Starting weupnp` / `Looking for Gateway Devices...` / `No gateways found` / `Stopping weupnp` |

该入口在 test_package 中被 `Upstream_Main_entrypoint` 用例覆盖（in-process 调用），
因此「上游可运行入口」已全部执行，无漏测。

> 按用户口径：上游没有自动化测试时，**明确说明没有测试入口**并附清点证据；
> `test_package` **不**用于冒充上游测试统计 —— 上游统计为 0，补全用例单独计 23 项。

## 三、构建工具链（T 类，非库依赖）

| 工具 | 状态 | 证据 |
|---|---|---|
| BiSheng JDK 17.0.13 | ✅ 可得 | `~/bishengjdk17/bin/java -version` → `openjdk 17.0.13 BiSheng` rc=0；`install-jdk.sh` http=200（sha256 `e324c090…3390b`） |
| Apache Maven 3.6.3 | ✅ 可得（官方归档） | `archive.apache.org` http=200，sha256 `26ad91d751b3a9a53087aefa743f4e16a17741d3915b219cf74112bf87a438c5` |
| `conan download maven/3.9.6 -r=ohpcd` | ❌ 无配方 | rc=1（`system acceleration policy not enabled`）；对照组 `zlib/1.3.1` rc=0 |
| `conan download bishengjdk/17.0.13 -r=ohpcd` | ❌ 无配方 | rc=1 |
| cmd-pkgs `install-maven.sh` | ❌ 不存在 | http=404 |
| 上游 `mvnw` wrapper | ❌ 不存在 | `find . -name "mvnw*"` → 0 |

⇒ 配方自行供给 JDK（cmd-pkgs，SHA-256 锁定）与 Maven（官方归档，SHA-256 锁定）。
