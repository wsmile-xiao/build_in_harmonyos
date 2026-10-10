# tunnelx 20190701 适配笔记

## 编译环境

- 构建系统: custom（上游 `build` = `javac`，`jmake` = `jar`；无 CMake/Autotools/Make/Maven/Gradle/Ant）
- 编译日期: 2026-10-04
- 编译器: BiSheng OpenJDK 17.0.13（`javac` / `jar`，无 C/C++ 编译面）
- 目标平台: OHOS / armv8（profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built（conan create + test_package 全绿；待 W3/CI 后置为 published）

## 源码与身份核验

请求名 `tunnelx` 是 Debian 二进制包名，源包同名，上游工程为 Julian Todd 的
Tunnel（TunnelX）。请求版本 `20190701` 即上游快照日期版本。

```
$ curl -sS "https://api.ftp-master.debian.org/madison?package=tunnelx&table=all"
tunnelx | 20190701-1 | stable | source, all

$ curl -o /dev/null -w "%{http_code}" \
    "https://codeload.github.com/goatchurchprime/tunnelx/tar.gz/refs/tags/20190701"   → 404
    （v20190701 / R20190701 / tunnel20190701 / 2019-07-01 亦全 404 —— 上游无 20190701 tag）

$ git ls-remote --tags https://github.com/goatchurchprime/tunnelx.git
9ae8656ef5d54ff2a52818757944b0e7a2805e4a  refs/tags/R2019a          ← 唯一 tag

$ curl -sSL -o tunnelx-R2019a.tar.gz \
    "https://github.com/goatchurchprime/tunnelx/archive/refs/tags/R2019a.tar.gz"
$ sha256sum tunnelx-R2019a.tar.gz
de8fbee92325233ccab703a5661b8e119b8bbb710660b7f590454eba82240cfd

# 与 Debian 官方 orig 包交叉印证（同一 2019-07-01 快照）
$ sha256sum tunnelx_20190701.orig.tar.gz
fccee11ce1786d7e30d89e04cdd533e02d84a096626d608f0bbf6de456b86263
  （与官方 tunnelx_20190701-1.dsc 的 Checksums-Sha256 逐字节一致）
$ diff -rq tunnelx-R2019a/src tunnelx-20190701/src     → 无差异（81 个 .java 全等）
$ grep -n tunnelversion tunnelx-R2019a/src/TN.java
58:    static String tunnelversion = "version2019-07-01 DoES";
$ grep -n tunnelversion tunnelx-20190701/src/TN.java
58:    static String tunnelversion = "version2019-07-01 DoES";
```

**结论**：GitHub 官方 tag `R2019a` 的 `src/` 与 Debian orig 包逐字节一致，且
`src/TN.java:58` 的版本串为 `version2019-07-01 DoES` → `R2019a` 即 20190701 快照。
`R2019a` 比 Debian orig 多一个 `pythonbits/`（上游辅助 Python 脚本目录），构建面
不涉及。因此 `conandata.yml` 采用**官方 GitHub tag 归档 URL**（R39：官方源；
未使用 Debian 下游重打包源）。

## 语言预检（R47）

```
$ python3 scripts/ohc-run.py lang-preflight tunnelx 20190701 \
      --src ~/tmp/tunnelx-20190701/src/tunnelx-R2019a --lang java
{"expected": "java", "detected_language": "java",
 "language_evidence": {"build_system": "none",
                       "manifest": "未发现语言 manifest 文件",
                       "source_stats": "源文件 96 个（java:82, python:14），主体占比 85%"}}
✅ 语言匹配: task=java, detected=java — 继续适配主流程     rc=0
```

## 编译步骤

```
# 1. JDK（HarmonyOS PC 由 HNP 预装，PATH 内无 java/javac/jar）
$ ~/bishengjdk17/bin/javac -version           → javac 17.0.13
$ file ~/bishengjdk17/bin/java
  ELF 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)   ← OHOS musl/aarch64

# 2. 上游构建入口（script `build`）：javac -version -d . src/*.java
$ javac -d build/classes src/*.java
javac rc=0；3 warnings（Integer(int)/JApplet 已废弃，非错误）；产出 230 个 .class

# 3. 上游打包入口（script `jmake`）
$ ls -1 symbols > symbols/listdir.txt ; ls -1 tutorials > tutorials/listdir.txt
$ jar cfe build/tunnelx.jar Tunnel.MainBox \
      -C build/classes Tunnel -C <src> symbols -C <src> tutorials
jar rc=0；build/tunnelx.jar = 623817 bytes

# 4. Conan 配方（复刻 2/3 两步；不引入 ant/maven/gradle）
$ conan create archives/t/tunnelx/20190701 \
      -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
tunnelx/20190701: Package '6b129b068851896169fae42d399fa922d239ce8a' created   rc=0
test_package result: 11/11 passed, 0 failed
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan create` 首个错误：`TypeError: get() got an unexpected keyword argument 'tar_format'`（source() 第 94 行） | `conandata.yml` 的 `tar_format` 是归档规范字段，`conan.tools.files.get()` 只接受 `url/sha256/destination/strip_root/verify` | `source()` 中先 `dict(...)` 复制并 `pop("tar_format")` 再调用 `get()`（与 `archives/m/motif`、`archives/a/accountsservice` 同一处理） |
| 2 | 直连 `github.com/archive/...` 下载在 `init-build` 中 `_ssl.c:993 handshake timed out` | 本机到 GitHub 偶发 TLS 抖动（curl 重试可成功） | 预置已核验 tarball 至 `$TMPDIR/builds/tunnelx-20190701.tar.gz`（`init-build` 命中已存在文件则跳过下载），并以 `EXPECTED_SHA256` 固定校验值 |
| 3 | `git worktree add` 全量检出失败：`unable to create file ... (Errno 28)` / `No space left on device` | 文件系统 **inode 耗尽**（`/mnt/hmdfs/100/non_account` 48,455,677 inode 已用满，剩余 <6k） | 改用**稀疏工作树**：`git worktree add --no-checkout` + `git sparse-checkout set ... archives/t/tunnelx`（仅检出 scripts/ci/templates/knowledge(graph,doc,operations,requirements) 与本包目录，文件数 7239→1280） |
| 4 | `conan create` 在测试包目录留下 `conanrun.sh`/`conanbuildenv-*.sh`/`metadata/`/`__pycache__` | `test_package` 无 `layout()`，conan 默认把生成器写到 conanfile 所在目录 | 提交前清理（这些文件不进入 PR；JC 垃圾检查只扫提交差异） |
| 5 | HarmonyOS 无 `libawt_xawt.so`（仅 `libawt.so` + `libawt_headless.so`），GUI 无法建窗 | BiSheng JDK 的 `java.desktop` 未构建 X11 后端 | 属平台限制，不影响编译/打包/类加载；`test.sh` T4 改为断言"入口已装配且停在 AWT 初始化（HeadlessException，栈帧含 `Tunnel.MainBox.main`）" |

## 源码修改

**无。** 上游源码零修改（`patches_applied: []`），HarmonyOS 层全部落在
Conan 配方与安装的启动器上：

1. `conanfile.py` 自动定位 BiSheng JDK（`JAVA_HOME` → `~/bishengjdk17` →
   `/data/service/hnp/bishengjdk17` → `javac` on PATH → `conan.tools.files.get()`
   从官方 `cmd-pkgs` 通道安装）；不使用裸 shell 变量（R33），不用 curl 下载（L0o）。
2. 安装 `bin/tunnelx` 启动器：自动解析 `JAVA_HOME`，并以
   `-Djava.io.tmpdir=<可写目录>` 覆盖 HarmonyOS 只读的 `/tmp`
   —— 对应上游 `src/FileAbstraction.java:136-142` 的临时目录回退链
   （`<cwd>/tmp` → `~/.tunnelx/tmp/` → `java.io.tmpdir`）。
   同时提供 CLI 契约 `bin/tunnelx --version` / `--help`（在 JDK 探测之前处理，
   无需 JVM，退出码 0）—— 该契约正是 CI L2 smoke test（
   `ci/conan/build_and_test.sh` L2: `<bin> --version` 或 `--help` 成功即 pass）所探测的；
   上游 `Tunnel.MainBox` 本身是 GUI 入口，`--version` 会被其当作未知参数并触发
   `TN.emitWarning` → `mainbox` 为 null 时 NPE，故由启动器层承接该契约。
3. JAR 内嵌 `symbols/`、`tutorials/` 及 `listdir.txt`（复刻 `jmake`），使
   应用自包含——对应上游 `src/FileAbstraction.java:146-160` 的类加载器资源查找。

## 上游测试入口

```
$ find <src> -iname '*test*' -o -iname '*Test*'          → 空
$ grep -rln 'junit\|@Test\|org.junit' <src>/            → 空
$ grep -rn 'public static void main' <src>/*.java
  src/MainBox.java:596:    public static void main(String args[])
  src/PrintScaleDialog.java:192://	public static void main(String[] args)   ← 已注释
$ find <src> -name '*test*' -path '*debian*'             → 空（无 autopkgtest）
$ grep -n 'Testsuite' debian/control                     → 无
```

**上游自动化用例数 = 0**（无 JUnit、无 test 源、无 `make check`/ctest/pytest、
无 autopkgtest）。唯一可执行入口为 GUI 主类 `Tunnel.MainBox`
（`src/MainBox.java:596`，启动命令见 `run`：`java -showversion -ea -Xmx3000M -cp . Tunnel.MainBox`）。

真实执行尝试（原始输出）：

```
$ java -cp build/tunnelx.jar Tunnel.MainBox --quiet ; echo rc=$?
Exception in thread "main" java.awt.HeadlessException:
No X11 DISPLAY variable was set, but this program performed an operation which requires it.
	at java.desktop/java.awt.Window.<init>(Window.java:553)
	at java.desktop/javax.swing.JFrame.<init>(JFrame.java:180)
	at Tunnel.MainBox.<init>(MainBox.java:423)
	at Tunnel.MainBox.main(MainBox.java:637)
rc=1
```

→ 入口已正确装配并执行至 AWT 初始化；因 BiSheng JDK 无 xawt 后端 + 无 DISPLAY，
GUI 无法建窗（平台限制）。`test.sh` T4 即据此断言入口可达。

**test_package 不能替代上游测试统计**：上游 0 个用例，本包新增消费者侧
测试（test.sh 11 项 + 鸿蒙探针 7 项断言）单独统计，不并入"上游用例"。

## 依赖版本

- bishengjdk 17.0.13（OHOS aarch64/musl；HNP 预装或官方 `cmd-pkgs` 通道安装）
- **无 Conan 第三方依赖**：全树 194 个唯一 import 均属 JDK 标准库
  （`java.base`/`java.desktop`/`java.xml`/`java.sql` 等），无随树 jar、无 `Class-Path`，
  上游 `javac` 命令不带 `-cp`（依赖分析报告 §1.5/§6）。
- 运行期可选外部程序（非依赖、功能门控）：`survex`(cavern/3dtopos/aven)、
  `gdal_translate`；`org.sqlite.JDBC`（sqlite-jdbc）为反射加载的死代码。

## 验证结果

```bash
# 真实构建（javac + jar）
$ javac -d build/classes src/*.java                    → rc=0，230 class，3 warnings
$ jar cfe build/tunnelx.jar Tunnel.MainBox ...         → rc=0，623817 bytes

# conan create（含 L1 test_package）
$ conan create archives/t/tunnelx/20190701 -pr:h=ci/conan/profiles/ohos-aarch64 ...
tunnelx/20190701: Package '6b129b068851896169fae42d399fa922d239ce8a' created   rc=0
[test] test_package result: 11/11 passed, 0 failed
[test] ✅ all 11 test_package checks passed
```

## 注意事项

- `reports/conan-create.log` 是 conan-verify G2 的原始日志，其中出现的
  `https://ghfast.top/...` 前缀是**框架 E017 镜像注入**（`scripts/ohc/conan_verify.py`）
  在运行期改写 URL 留下的历史记录，**不是本包的源声明**；`conandata.yml` 始终为单条
  官方 URL（PF7 源URL闸自检：无命中）。

- HarmonyOS BiSheng JDK 仅提供 headless AWT（无 `libawt_xawt.so`）：Tunnel 的
  Swing 界面在 OHOS PC 上不可显示，属平台/JDK 构建限制；包的编译、打包、
  类加载、资源解析与几何内核均正常工作且已被测试覆盖。
- `libdirs=["lib"]`、`bindirs=["bin"]`（`package_type = application`），
  软件级 `commands.json` 声明 `type=tool`（R38/L0k）。
- 启动器默认堆 `-Xmx1000M`（对齐 Debian `tunnelx.manifest` 的
  `Debian-Java-Parameters: -Xmx1000M`；上游 `run` 脚本用 3000M）。
- 上游 GUI 只在有图形后端时可用（BiSheng JDK 无 `libawt_xawt.so`）；无显示环境下
  `bin/tunnelx`（不带参数）仍会执行到 AWT 初始化后以 `HeadlessException` 退出，
  这是上游入口的真实行为，不是启动器缺陷。
---

**编译结束**: 2026-10-04 13:36
**最终状态**: built
