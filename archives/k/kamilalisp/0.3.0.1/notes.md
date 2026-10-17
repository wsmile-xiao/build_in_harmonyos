# kamilalisp 0.3.0.1 — HarmonyOS PC 适配笔记

## 概述
- 上游：https://github.com/iczelia/kamilalisp ，tag `v0.3.0.1`（commit `f0aef41`）。
- 语言/构建：**纯 Java 17 + Maven**（无 C/C++/Rust/Go 源文件），产物 `kamilalisp-0.3.jar`
  （fat JAR，`Main-Class: palaiologos.kamilalisp.repl.Main`）。
- 分类：CLI / 解释器（R38 需 commands.json）。

## 上游测试
- JUnit 5（junit-jupiter 5.9.3）+ maven-surefire-plugin 3.1.2。
- 22 个测试类 + `Common.java`，**实测 102 个用例全部通过**：
  `Tests run: 102, Failures: 0, Errors: 0, Skipped: 0`。
- 命令：`mvn clean package -B -DskipTests=false -Dproguard.skip=true -Duser.home=$HOME`。
- 日志：`.task-kamilalisp/logs/upstream_mvn_test.log`、逐用例明细 `upstream_tests_summary.txt`。

## OHOS 平台适配（真实问题 → 根因 → 修复）
1. **JVM `user.home` = "?"**
   - 现象：Maven 提示 `Reading user settings from ?/.m2/settings.xml`，本地仓库落在
     `?/.m2/repository`，镜像不生效、依赖反复下载。
   - 根因：BiSheng JDK 17 在 OpenHarmony 上无法解析 `user.home`（`-XshowSettings` 显示 `user.home = ?`，
     `os.name = HarmonyOS`）。
   - 修复：build() 显式传 `-Duser.home=$HOME`。

2. **ProGuard OOM（result=137）**
   - 现象：`proguard-maven-plugin:2.6.0:proguard` 失败 `Obfuscation failed (result=137)`。
   - 根因：ProGuard 7.3.2 以 `-optimizationpasses 9` 混淆 36MB fat JAR 在鸿蒙 worker 上被
     SIGKILL（137，内存不足）。
   - 修复：`-Dproguard.skip=true`（混淆为非功能性打包步骤；保留功能完整的 shaded JAR）。

3. **工具链获取（无 curl 字面量，满足 CI L0o）**
   - 优先探测 `JAVA_HOME` / `~/bishengjdk17` / `~/.local`；缺失时经 conan `download()` 拉取
     cmd-pkgs `install-jdk.sh` 安装 BiSheng JDK 17.0.13。
   - Maven 优先探测 `~/maven/bin/mvn` 等；缺失时经 conan `download()` 拉取
     apache-maven-3.6.3（校验 SHA256）并解压。

## 打包内容
- `libexec/kamilalisp-0.3.jar`（fat JAR）
- `bin/kamilalisp`（CLI 启动器，查找 JAVA_HOME/java 后 `exec java -jar`）
- `licenses/LICENSE`（GPL-3.0）

## 测试入口（test_package，consumer 视角）
- `test.sh`：经由 `bin/kamilalisp` 运行 `test_kamilalisp.lisp`，断言
  `(+ 1 2)=3`、`(* 6 7)=42`、`(reverse "KamiLisp")=psiLimaK`、解释器干净退出，
  外加 **1 个 HarmonyOS 平台专属断言**（JVM `os.name == HarmonyOS`）。
- 共 5 条断言（含 1 条鸿蒙特有）。

## 备注
- 本库为纯 Java 项目，按 R47 语言预检判定为 `env_unsupported`（非 C/C++）；
  本次适配依据用户明确授权并参照仓库既有 Java 配方（airlift-slice/t-digest/vinnie/weupnp）路径执行。
---

**编译结束**: 2026-10-10 20:19
**最终状态**: built
