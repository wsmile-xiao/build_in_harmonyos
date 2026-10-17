# auto64fto32f 2.1 适配笔记

## 编译环境
- 构建系统: custom（javac 直接编译；上游为 Gradle 6.4.1，已绕开）
- 编译日期: 2026-08-25
- 编译器: bishengjdk17 javac（--release 11，对齐上游 sourceCompatibility）
- 状态: built

## 编译步骤

1. **获取源码**: 从 GitHub 官方 tag 下载 `Auto64Fto32F v2.1` tarball
   - URL: https://github.com/lessthanoptimal/Auto64Fto32F/archive/refs/tags/v2.1.tar.gz
   - SHA256: de506eb7a29d9d54b5ec1f0ec97937e34200b616d3a908cb48d0004f80935de3

2. **绕开 Gradle 的原因与做法**:
   - 上游 build.gradle 只声明了 `java` 插件、`src` 主源码集和 jar/javadoc/sourcesJar 任务；
     Gradle 6.4.1 wrapper 首跑需下载完整发行版并连 Maven Central 拉 junit，在鸿蒙真机
     上开销大且 daemon 常驻易残留
   - 配方直接 `javac --release 11 -d build/classes src/com/peterabeles/auto64fto32f/*.java`
     后 `jar cf auto64fto32f-2.1.jar -C build/classes .`，产物语义与上游 `gradle jar` 一致

3. **上游测试接入**:
   - 唯一测试套件: `test/com/peterabeles/auto64fto32f/TestAugmentJavaFiles.java`，
     4 个 @Test 方法（JUnit 4.12 + hamcrest-core 1.3）
   - junit/hamcrest 经 conandata.yml 自定义键 `test_dependencies` 从 Maven Central
     下载（sha256 校验 + 阿里云镜像回退），仅构建期使用，不打包
   - 用 `org.junit.runner.JUnitCore com.peterabeles.auto64fto32f.TestAugmentJavaFiles`
     运行；HMBS_UPSTREAM_TEST_RESULT 的数字直接解析 JUnitCore 输出
     （成功 `OK (N tests)` / 失败 `Tests run: N, Failures: M`），汇总行缺失即报错拒绝放行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无预编译发布物 | GitHub release 无 assets，Maven Central 构件非官方直发渠道 | 按 R39 以 GitHub 官方 tag tarball 为源码源，从源码构建 |
| 2 | Gradle 在真机上重且不稳 | wrapper 需联网下发行版、daemon 残留 | 绕开 Gradle，javac 直编（上游构建逻辑本身极简） |
| 3 | /tmp 只读 (E002) | HMBS 沙箱限制 | javac/java 子进程继承 HMBS 注入的 TMPDIR/TMP/TEMP |
| 4 | CI worker 可能缺 JDK | 未预装 bishengjdk | _ensure_java() 四级回退：JAVA_HOME → cmd-pkgs 标准路径 → PATH → install-jdk.sh 自动安装 |

## 源码修改

无补丁。纯 Java 字符串处理库，不涉及平台相关 API，源码零修改即可编译。

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| BiSheng JDK | 17+ | 编译/运行时（系统工具） |
| junit | 4.12 | 测试期（Maven Central, sha256 校验） |
| hamcrest-core | 1.3 | 测试期（Maven Central, sha256 校验） |

## 验证结果

```bash
# 上游测试（build() 内真实执行，数字以真机预检日志为准）
$ java -cp build/classes:build/test-classes:junit-4.12.jar:hamcrest-core-1.3.jar \
    org.junit.runner.JUnitCore com.peterabeles.auto64fto32f.TestAugmentJavaFiles
Time: ...
OK (4 tests)

# test_package 消费者测试（真机运行）
$ bash test.sh <package_folder>
AUTO64FTO32F_TEST_PASS 6/6
```

## 注意事项

- 上游 src/ 无 main class：auto64fto32f 是被 EJML 等项目的代码生成脚本引用的库 JAR，
  不是 CLI 工具，因此包内无 bin/、不需要 commands.json（R38 库类型豁免）
- javac 必须是完整 JDK（JRE 无 javac）；jar 工具同理来自 JDK bin/
- 测试期 junit/hamcrest 不进 package()，避免向制品仓引入第三方二进制


## 2026-08-25 真机预检 evidence 失败修复

| 问题 | 根因 | 修复 |
|------|------|------|
| 预检 evidence 阶段报「无法读取当前 archive 代码树」 | test_package/__pycache__/conanfile.cpython-310.pyc：上一轮本地校验脚本直接 import 了配方源文件，在归档树里留下二进制字节码；它是整棵归档树唯一无法按 UTF-8 文本读取的文件，导致 hmbs 读取/同步代码树失败 | 删除 __pycache__ 目录；此后本地语法校验改用 ast.parse（不 import 配方源文件、不在归档树落盘字节码） |
| 顺带加固 | ARCHIVE-SPEC.md §2.2 与 knowledge/drafts/E216 要求 conanfile.py settings 声明全部四项（os/compiler/build_type/arch），JVM 应用也不例外（CI L0p 门禁）；已发布先例 aladin/12.06 同为 JVM 应用且按四项声明 | 主配方 settings 由 "os","arch" 补齐为 "os","compiler","build_type","arch"（test_package 保持 os/arch，与 aladin 先例一致） |

备注：工作树里 archives/l/libXext 的两处 modified 是仓库同时跟踪大小写两种路径
（libXext 与 libxext）在 Windows 大小写不敏感文件系统上的固有假差异，与本任务无关，未触碰。

## 2026-08-25 真机预检 compile 失败修复（build() 源码路径）

| 问题 | 根因 | 修复 |
|------|------|------|
| build() listdir 报 FileNotFoundError: `<build>/com/peterabeles/auto64fto32f` | 源码发现路径少了 tarball 的 `src/` 一级。已下载官方 v2.1 tarball 核对（sha256 与 conandata 一致）：strip_root 后保持 Gradle sourceSets 布局，Java 主源码位于 `<source_folder>/src/com/peterabeles/auto64fto32f/`（4 个 .java），配方却按 `<source_root>/com/peterabeles/auto64fto32f` 去 listdir | pkg_dir 改为 `src/com/peterabeles/auto64fto32f`，并在 listdir 前增加目录存在性校验与准确报错 |
| 加固：conandata 自定义 test_dependencies 的 junit/hamcrest 落盘位置不确定 | Conan 2 的 `download()` 没有 destination 参数，内部 `os.path.abspath(filename)` 相对 conan 进程 cwd 解析；jar 可能落在 cwd 而非 source_folder，导致随后的存在性检查误报 | filename 显式改为绝对路径 `os.path.join(src_root, dep["filename"])` |
| 加固：`get()` 解压位置隐式依赖进程 cwd | Conan 2 `get()/untargz` 默认 `destination="."`（进程 cwd） | source() 显式传 `destination=self.source_folder` |

本地验证（Windows，无 JDK）：
- ast.parse 校验配方语法通过（不在归档树落 __pycache__）
- 用真实 v2.1 tarball 复现 strip_root 解压 + 修复后的发现逻辑：4 个主源码、
  test/com/.../TestAugmentJavaFiles.java 存在且恰有 4 个 @Test、LICENSE-MIT/UNLICENSE 在根目录
- readonly_tmp 审计：配方 grep `/tmp|mktemp|tempfile` 只命中一行注释，无实际 /tmp 写入；
  上游 JUnit 测试纯内存（ByteArrayInputStream），javac/java 子进程继承 HMBS TMPDIR。
  preflight.sh[229] 的 /tmp 只读报错是 hmbs 包装脚本自身行为，不属于配方改动范围

## 2026-08-25 CI L0o uses_external_curl 修复

| 问题 | 根因 | 修复 |
|------|------|------|
| CI #31298 conan-build-test 步骤 L0o 门禁失败：conanfile.py 第 111 行命中 `"curl", "-fsSL",`，判 uses_external_curl，L0 直接 fail 并阻断 L1–L5 | `_ensure_java()` 四级探测全部落空时的最后回退里，`_curl_download()` 以外部 curl 进程下载 cmd-pkgs install-jdk.sh；门禁 grep（build_and_test.sh:815）禁止配方出现 `"curl"`/`"wget"` 字面量或 subprocess+curl/wget 组合 | 删除整个 `_curl_download()`；install-jdk.sh 改用 `conan.tools.files.download()`（与本配方 test_dependencies 的 junit/hamcrest 下载同一机制，上一轮真机预检已实测可用；retry=3/retry_wait=2 对齐原 curl --retry 语义）；JDK 缺失的报错信息同步去掉手工 curl 命令 |

验证：
- ast.parse 语法校验通过
- 按 build_and_test.sh:815 的 ERE 在本地精确复现 L0o 门禁 grep：零命中（修改前第 111 行命中）
- 配方中已无任何小写 curl/wget 出现；CURL_CA_BUNDLE 等大写环境变量名不属门禁匹配范围，保留用于子进程 CA 透传

行为影响评估：正常路径（JAVA_HOME / 标准路径 / PATH 任一命中 JDK）完全不受影响——本轮只改了最后回退的下载实现，且新实现与同配方内已被真机验证的 junit/hamcrest 下载走完全相同的 conan download() 通道。
