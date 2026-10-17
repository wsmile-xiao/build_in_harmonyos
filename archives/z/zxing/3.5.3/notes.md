# zxing 3.5.3 适配笔记

## 来源与许可证

- 官方仓库：`https://github.com/zxing/zxing`
- 官方 tag：`zxing-3.5.3`（annotated tag，tag 对象 `2d608639c944a5b17363706fe5e9055bab0d6c2f`，
  拨离后提交 `f0f1a94439db0300ff0c4618f4e0a41aa630aeac`）
- 官方源码归档：`https://github.com/zxing/zxing/archive/refs/tags/zxing-3.5.3.tar.gz`
- 官方源码归档 SHA-256：`0ff6194b8f9f7346c48922ce04f6a037b21435a739a7b526e097a69cf019816b`
- 许可证：Apache-2.0（`LICENSE` + `NOTICE` 都进 Conan 包的 `licenses/`）

### 源身份三路互证（sha256 三路 + 版本同一性三路）

| 路 | 读数 |
|----|------|
| 路①本机首次下载 | `curl -sSL -o zxing-3.5.3.tar.gz <url>` → 133115974 B，`sha256sum` = `0ff6194b…019816b` |
| 路②独立第二次下载（短形态 URL `…/archive/zxing-3.5.3.tar.gz`，全新连接） | `curl … \| sha256sum` = `0ff6194b…019816b`（与路①逐字节一致） |
| 路③独立实现复算 | `python3 hashlib.sha256` 与 `openssl dgst -sha256` 均 = `0ff6194b…019816b` |
| 版本同一性 A：上游全 tag 形态 | `git ls-remote --tags https://github.com/zxing/zxing.git` → `zxing-3.5.3` 命中（拨离提交见上） |
| 版本同一性 B：第三方发行清单 | Maven Central `com.google.zxing:core` 的 `maven-metadata.xml` 含 `<version>3.5.3</version>`，`core-3.5.3.pom` HTTP 200 |
| 版本同一性 C：包内自述 | 归档根 `pom.xml` 与 `core/pom.xml` 的 `zxing-parent`/`core` 版本均为 `3.5.3` |

### 为什么不是 zxing-cpp（另一权威 repo，已逐一排除）

- `recipes/zxing` 在 conan-center-index **不存在**（raw `config.yml` 404）；`recipes/zxing-cpp` 只保留 `3.1.1`。
- `git ls-remote --tags https://github.com/zxing-cpp/zxing-cpp.git` 共 27 个 tag，
  形态为 `v1.0.0 … v3.1.1`，**无任何 3.5.x**；`codeload …/zxing-cpp/tar.gz/refs/tags/v3.5.3` → HTTP 404。
- 平台任务面同样把两者分开：`contrib-6798 zxing-cpp/2.3.0`（`sourceUrl=https://github.com/zxing-cpp/zxing-cpp`，已 done）
  与本任务 `contrib-12431 zxing/3.5.3` 是两条独立任务；本仓库也已有
  `archives/z/zxing-cpp/2.3.0`（C++ 库）。本任务包名 `zxing`、版本 `3.5.3`，唯一命中的权威源是
  `zxing/zxing` 的 `zxing-3.5.3`。

### 语言预检（R47）两种口径都留读数

- 缺省口径（任务卡 `lang=cpp`）：`ohc-run.py lang-preflight zxing 3.5.3 --src <src>` → **rc=2 / `status=env_unsupported` /
  `detected_language=java`**（evidence：`build_system=gradle/maven`、`manifest=build.gradle*/pom.xml 存在`、
  `源文件 528 个（java:515, nodejs:13），主体占比 98%`）。该次终态被工具按默认解析链写进
  设备共享单槽 `$HOME/ohpcd-ai-worker-result.json`（backlog #75 同族），已按该 backlog 的任务侧最低限度
  **备份到 `$TASK_DIR/logs/shared-result-backup-langpf-rc2.json` 后删除共享槽文件**，避免覆盖并行任务结果。
- 正式口径：`--lang java` → **rc=0 / `milestone=lang_checked`**（读数落 `$TASK_DIR/logs/lang-preflight-java.json`）。
- 依据：平台 `lang` 枚举中 `java` 任务全部落在 `lang_hold`（`GET /api/tasks?lang=java` → total 4，均为
  `status=lang_hold`），而批量导入任务一律 `lang=cpp`；仓库内既有 Java 包 `weupnp 0.1.4`（平台任务
  `contrib-11874 lang=cpp status=done`，2026-10-02 合入）、`t-digest`、`vecmath`、`aladin`、`jflex`、
  `jackson-jr` 均按 `detected_language=java` 完成适配。处置与 `relic 7.6.1` 先例一致：
  两种口径都留读数，正式口径按 detected 申报。

## 构建设计

- 配方只构建并交付上游 **`core` 模块**（`com.google.zxing:core`，条码编解码库本体，**运行期零第三方依赖**）。
- 构建入口是 **`cd <src>/core && mvn … clean verify`**，不改任何上游源码（零补丁）。
- 工具链：BiSheng JDK 17.0.13（ohos-aarch64 归档，SHA-256 锁定，与 `archives/j/jackson-jr`、
  `archives/w/weupnp` 同一组 URL/SHA）+ Apache Maven 3.6.3（官方归档，SHA-256 锁定）。
  两者都不进包，只作为构建期工具按需下载。
- `-Dos.name=Linux` 经 `JAVA_TOOL_OPTIONS`/`MAVEN_OPTS` 注入：OpenHarmony PC 上 JVM 自报
  `os.name=harmonyos`，Maven/Surefire/java.awt 会判为不支持平台。
- `package_type = "unknown"`：Java 制品没有 static/shared 语义，声明 `library` 会让 Conan 2
  强制要求 `shared` 选项（`weupnp` 实测，与 `jackson-jr` 同口径）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 从仓库根跑 `mvn -pl core …` 在读模型阶段即失败：`Non-resolvable parent POM for com.google.zxing:zxingorg:3.5.3-SNAPSHOT` | 根 `pom.xml` 的 `zxingorg` profile 以 `<jdk>[17,)</jdk>` 激活（本机/配方都是 JDK 17），把 `zxingorg` 模块拉进 reactor；而该发布 tag 上 `zxingorg/pom.xml` 的 parent 版本**仍写着 `3.5.3-SNAPSHOT`**，与父 POM 实际版本 `3.5.3` 不一致，模型解析直接 fatal | 改为 `cwd=<src>/core` 单模块构建（Maven 只读 `core/pom.xml` 与其 `../pom.xml` 父 POM，不聚合兄弟模块）；**不改上游源码、不加 `-P` 掩盖**，配方里写明原因 |
| 2 | 直接跑 `mvn` 依赖 exec 位与 shell | HMDFS 上抽取文件的可执行位不保证（`notes/device-facts.md` §一.27 同族） | 配方 `_maven_command()` 先 `os.access(X_OK)` 自检，不可执行时回退 `["/bin/sh", mvn_script]` |
| 3 | `lang-preflight` 缺省口径 rc=2 并写共享 result 单槽 | 工具 rc=2 分支没有 `--out` 就落 `$HOME/ohpcd-ai-worker-result.json`（backlog #75） | 备份到 `$TASK_DIR/logs/` 后删除共享槽文件；正式口径加 `OHC_RESULT_OUT=$TASK_DIR/logs/lang-preflight-java.json` 重定向 |

## 上游测试

沙箱 `HOME=$TASK_DIR/test-home`、`JAVA_TOOL_OPTIONS=-Dos.name=Linux`、
`mvn -B -ntp -Dstyle.color=never -Djava.awt.headless=true clean verify`（cwd=`<src>/core`）：

- 构建：`BUILD SUCCESS`，`Total time: 09:12 min`，rc=0
- Surefire：**131 个测试类 / 542 个用例 / 0 失败 / 0 错误 / 0 跳过**
  （`core/target/surefire-reports/TEST-*.xml` 131 份，`tests` 求和 = 542）
- 源码侧：`core/src/test` 141 个测试源文件、`@Test` 注解 **490** 处、断言语句调用点 **937** 处
- 差额归因：542 − 490 = **52**。54 个 `*BlackBox*TestCase` 子类自身 0 个 `@Test`，用例继承自
  `AbstractBlackBoxTestCase` / `AbstractNegativeBlackBoxTestCase`（这 2 个抽象基类贡献了源码侧 2 个 `@Test`
  但不单独生成 suite），故 `54 − 2 = 52`
- 上游当前 HEAD（`33dfdef`，2026-10-06 浅克隆）同口径源码 `@Test` = **541**，作为 rule4 下界 ≤ 声明 N=542
- 断言数 937 属**另一口径**（断言语句 ≠ 测试用例），按「四种口径不得混用」单列，不参与 N

## 产物

- `lib/zxing-core-3.5.3.jar`（611275 B，上游 `core/target/core-3.5.3.jar` 改名交付，
  避免 `core-3.5.3.jar` 这种无语义名与其他包冲突）
- 291 个 class 全部 major=52（Java 8），`META-INF/MANIFEST.MF` 含
  `Automatic-Module-Name: com.google.zxing` 与完整 OSGi `Bundle-*` 头
- `licenses/LICENSE`、`licenses/NOTICE`、`share/doc/zxing/README.md`
- 无 `bin/`：G2 后 L2（smoke）/L4（ELF 安全扫描）按「纯库包无 bin/」分支通过，ELF 面不适用
  （JVM 包无原生二进制），实物补测证据见 `test_package` 与 `reports/`

## 依赖

- **Conan 运行期/编译期依赖 0**（`requirements()` 为空；`com.google.zxing:core` 上游只声明
  `junit:junit` 的 `test` scope）
- 构建期工具：BiSheng JDK 17.0.13、Apache Maven 3.6.3（均 SHA-256 锁定、按需下载、不进包）
- 构建期从 Maven Central 取插件与测试构件，不引入任何需 Conan 前置适配的硬依赖
  （`bash ci/scripts/preflight_check.sh zxing/3.5.3` → `预检通过（无依赖需要检查）`）
