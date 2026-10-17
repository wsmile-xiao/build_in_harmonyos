# melting 5.2.0 — 适配笔记

> 申请人：yinuoguo，队伍：干
> 状态：built（待 HMBS 真机预检回填证据后由后端提交）
> 构建系统：Ant + Java

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | melting |
| 版本 | 5.2.0 |
| 上游仓库 | https://www.ebi.ac.uk/biomodels/tools/melting/（源码经 Debian orig 分发） |
| 源码 | https://deb.debian.org/debian/pool/main/m/melting/melting_5.2.0.orig.tar.gz |
| SHA256 | a3633c8f74ce383bbc3a339f99081a76c6529c10d9bdff1ad91b63e6d919a7bb |
| 镜像 | https://mirrors.edge.kernel.org/debian/pool/main/m/melting/melting_5.2.0.orig.tar.gz（同字节，已实测可达） |
| 构建系统 | Ant（build.xml：compile/jar/guijar） + Java |
| 许可证 | GPL-2.0-only |

## 二、上游测试审计（无自动化测试）

审计 `melting_5.2.0.orig.tar.gz`（top dir `MELTING5.2.0`，1299 entries）：

1. `build.xml` 仅定义 `init/prepare/prepare-src/clean/compile/jar/guijar/javadoc`（无 test 目标），`buildProject.sh` 仅 `ant compile/jar/guijar/javadoc`。
2. 无 `pom.xml`，抽查 `MainTest.java`、`MainTestApproximativeMode.java` 均无 junit/testng/`@Test` 导入。
3. `src/examples/MainTest*.java` 共 27 个，均为 `public static void main` 手动示例（如 `MainTestPerfectMatching` 调用 `MainTest.displayResults` 打印 Tm），无断言、无 harness。
4. `src/examples/test/*.txt` 为输入序列，`testResults/*.ods` 为文献 Tm 电子表格，均不被任何测试 harness 执行。
5. `src/` 外无 `*Test.java`（除 examples 外数量为 0），共 182 个 `src/**/*.java`。

结论：上游无自动化测试套件（discovered=0/executed=0），`build()` 不调用上游测试但输出 `status:"no_tests"` 标记，覆盖由 `test_package` 消费者 API 测试补全。

## 三、适配修正记录

### 修正 1：build.xml Java 1.8 兼容（replace_in_file）

- **问题**：`build.xml` 中 `javac source="1.5" target="1.5"`，现代 JDK（含 bishengjdk 17）已移除 1.5 支持，`ant jar` 会报 `Source option 5 is no longer supported`。
- **修复**：`build()` 内 `replace_in_file(build.xml, 'source="1.5" target="1.5"' -> 'source="1.8" target="1.8"')`（最小可移植改动，不改源码逻辑）。
- **方式**：配方内原地替换，不再使用 conandata patch。原因：原 patch 的 hunk 头为 `@@ -30,7`，而 compile 目标实际在 43 行附近，conan 严格打补丁时按行号命中 `prepare-src` 段报 `source file is different - build.xml`；字符串替换不受行号/上下文漂移影响，已用真实源码包本地验算替换前后各仅一处命中。

### 环境准备（复用 airlift-slice 模式）

- JDK：优先 `JAVA_HOME`，其次 `~/bishengjdk17` 等 cmd-pkgs 路径，再试 PATH，最后经 cmd-pkgs `install-jdk.sh` 自动安装 bishengjdk 17.0.13。
- Ant：优先系统 `ant`，缺失时从 `archive.apache.org` 下载 `apache-ant-1.10.14-bin.tar.gz`（sha512 校验）解压到 `~/ant`。
- 沙箱：透传 HMBS `TMPDIR/TMP/TEMP` + CA bundle，`curl` 失败时 `-k` 回退（与 airlift-slice 同源）。

## 四、编译命令

```bash
ant jar
ant guijar
```

产物：`build/melting5.jar`（Main-Class `melting.Main`）、`build/melting5GUI.jar`，`Data/*.xml` 热力学参数表随包发布到 `share/melting/Data`（运行时经 `NN_PATH` 指向）。

## 五、test_package 验证

`TestMelting.java` 调用 `melting.Main.getMeltingResults`（与上游 `MainTest.getMeltingTest` 同路径）：

- 用例 1：`CCATCGCTACC`（上游 `DNANoSelfComplementary.txt`，TmExp 67.6），断言 Tm∈(0,150)、enthalpy/entropy 非零。
- 用例 2：`GCGAGC`（同文件，TmExp 33.2），同上 3 断言。
- 共 6 断言 + 1 PASS，`test.sh` 编译运行并输出 `HMBS_TEST_PACKAGE_RESULT`（discovered/passedCount=6）。

## 六、交付物

| 路径 | 说明 |
|------|------|
| `libexec/melting5.jar` | 主产物 |
| `libexec/melting5GUI.jar` | GUI 产物 |
| `share/melting/Data/*.xml` | 热力学参数表 |
| `bin/melting`、`bin/melting-batch`、`bin/melting4` | 上游 wrapper 脚本 |
| `licenses/README`、`licenses/GeneralPublicLicence` | 许可证 |

## 七、注意事项

- 纯 Java 工具包，需 JVM 运行（bishengjdk 17）。
- `settings` 保留完整四项以通过 L0p，`validate()` 按 R32 检查 `os in (Linux, OHOS)`。
- `package_type = application` + `cpp_info.bindirs = ["bin"]`，软件级 `commands.json` 已声明。
- 本轮仅完成未提交工作树，真机证据（`HMBS_UPSTREAM_TEST_RESULT` no_tests + `HMBS_TEST_PACKAGE_RESULT` 6/6）待 HMBS 预检回填后写 PR 正文通过率。
- 2026-10-01 真机 test_package 失败 `/bin/sh: bash: inaccessible or not found`：真机仅提供 /bin/sh，无 bash；已将 test_package/conanfile.py 改为 `sh test.sh`，test.sh 改为 POSIX sh（shebang #!/bin/sh，去掉 pipefail，展开嵌套 :- 默认值），marker command 同步为 `sh test.sh`。
- 2026-10-01 真机 test_package 报 `JAR not found at .../test_package/package/libexec/melting5.jar`：test() 未传包路径，回退到 `$(pwd)/package`；已改为 `self.dependencies["melting"].package_folder` 作为 $1 传给 test.sh（此前脚本能被执行，cwd 假设成立，仅包路径错误）。
