# DRAFT-ohos-jvm-user-home-question-mark-tool-user-cache-cwd-relative：OHOS 设备 JVM `user.home` 为 `"?"`，Maven/Gradle 用户级缓存落到 cwd 相对 `?/.m2`

> Contributor: GoliWie | Status: Draft | Updated: 2026-09-25
> Source: feat(jline3): 3.3.1 适配 HarmonyOS PC（BiSheng JDK 17.0.13 + Maven Wrapper 构建）
> 对应：`knowledge/drafts/DRAFT-ohos-jvm-user-home-question-mark-tool-user-cache-cwd-relative.kv`

## 现象

在 OHOS PC 设备上首次用 Maven Wrapper 构建 Java 项目时，发行版与本地仓库
没有出现在预期的 `~/.m2`，而是出现在**项目目录下**一个名为 `?` 的目录里：

```console
$ ls
?/  pom.xml  ...
$ find . -maxdepth 4 -name '*.m2*'
?/.m2/wrapper/dists/apache-maven-3.3.9-bin/<hash>/apache-maven-3.3.9-bin.zip
?/.m2/repository/org/apache/maven/...
```

同时 JVM 属性实证（注意：此时 `HOME` 环境变量已正确 export）：

```console
$ java -XshowSettings:properties -version 2>&1 | grep user.home
    user.home = ?
```

## 根因

OpenJDK 在 Linux 上通过 `getpwuid_r(getuid())` 取 passwd 条目的 `pw_dir`
作为 `user.home`，取不到时回退为**字面量 `"?"`**（`os_linux.cpp` 的历史
行为）。OHOS 设备的应用侧 uid（实测 20001006）不在 `/etc/passwd` 中，
于是：

1. `user.home` = `"?"`——一个 cwd 相对路径；
2. JVM **不会**回退读 `HOME` 环境变量，`export HOME=...` 不生效，这是
   排查时最大的歧义来源；
3. 一切按 `user.home` 拼路径的工具随之把用户级缓存写到 `<cwd>/?/...`：
   - Maven：本地仓库 `<cwd>/?/.m2/repository`；
   - Maven Wrapper：发行版缓存 `<cwd>/?/.m2/wrapper/dists`（内含解压的
     apache-maven，首次运行还会 `Set executable permissions`）；
   - Gradle/sbt/leiningen 等同理。

后果：

- **缓存按 cwd 割裂**：每个构建目录各下载一份依赖（conan build 目录每次
  重建即冷缓存），无法跨 run 复用；
- **源码树污染**：构建后项目目录里留下名为 `?` 的垃圾目录（junk check
  风险点）；
- 直接读 `System.getProperty("user.home")` 的应用代码在设备上行为异常。

桌面 Linux/WSL 上 uid 在 `/etc/passwd` 中，不复现——这是 OHOS 设备环境
特性，非某库缺陷。与早期"h2/jna 适配需要 Maven cache 目录避开 HOME/权限"
的经验一致。

## 正确做法：显式指定全部用户级路径

构建命令不依赖 `user.home`，把工具的落盘位置显式钉死（Maven 用 JVM 属性
`-Duser.home`，对 wrapper 进程与 Maven 本体同时生效）：

```bash
# conan 配方 build() 内（build 目录相对定位，不写设备绝对路径）
$JAVA/bin/java -Xmx768m \
  -Duser.home="$BUILD_FOLDER" \
  -classpath "$SRC/.mvn/wrapper/maven-wrapper.jar" \
  -Dmaven.multiModuleProjectDirectory="$SRC" \
  org.apache.maven.wrapper.MavenWrapperMain \
  -B -Dmaven.repo.local="$BUILD_FOLDER/m2-repository" \
  clean verify
```

- Maven 本地仓库 → `-Dmaven.repo.local=<build>/m2-repository`；
- Wrapper 发行版缓存 → 被 `-Duser.home=<build>` 带到 `<build>/?/.m2`
  （可接受的 build 目录内自包含残留，随 conan build 目录生命周期清理）；
- Gradle 场景 → `--gradle-user-home <dir>` 或 `GRADLE_USER_HOME`；
- 判别：构建日志出现 `<项目目录>/?/.m2/...` 即命中本条。

jline3 3.3.1 实测：钉死后每次构建自包含可重现，全量 `clean verify`
（30 套件 155 用例）在设备上稳定通过。

## 禁止

- **禁止**用软链/拷贝 `.m2` 到固定路径来"修" `user.home`——掩盖环境事实，
  跨 worker 语义不成立；
- **禁止**把"已 export HOME"当作已修复的判据——JVM 的 `user.home` 不回退
  读 `HOME`，必须用 `-XshowSettings:properties` 实证；
- conan 配方交付文件中**禁止**硬编码设备绝对路径作为缓存目录（用 build
  目录相对定位）。

## 关联条目

- E338（同平台事实的 native 侧兄弟条目：同一 getpwuid 缺陷在 C/C++ 侧
  表现为 `homedir()` 返回 NULL、程序启动 SIGSEGV；本条为 JVM 侧
  `user.home` 回退为字面量 `"?"`。机制同源、语言层表现不同，互链不去重）
- E184（构建工具需手动安装；同属 Java 构建环境类，根因不同）
- E390（设备无 unzip；同为环境缺口类）
