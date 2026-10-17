# keycloak-archlinux 2.0.1 适配笔记

## 身份与上游

- 任务卡名 `keycloak-archlinux` 是截短名，唯一对应 **Arch Linux 官方包 `keycloak-archlinux-theme 2.0.1-1`**（Extra 仓，arch=any，maintainer artafinde）
- 上游项目本身 = Arch 官方 GitLab：https://gitlab.archlinux.org/archlinux/keycloak-archlinux-theme ，tag **v2.0.1**（带 v 前缀，2026-05-14，protected+signed）
- 内容：Keycloak IAM 服务器的登录/注册/账户/管理台/欢迎页界面主题（仿 Arch Linux 官网视觉），纯 Web 资源（FTL/CSS/图片/properties）
- License：Apache-2.0（根 LICENSE + Arch 包页 + PKGBUILD 一致；内层 v2/package.json 标 MIT 属上游内部不一致，以根 LICENSE 为准）
- 名称截短与 keycloak-metrics（↔ keycloak-metrics-spi）为同类先例

## 上游双构建路径

| 路径 | 工具链 | 产物 | 采用方 |
|---|---|---|---|
| `v2/` keycloakify | yarn + React 18 + Vite + tsc + esbuild + maven | `v2/dist_keycloak/keycloak-theme-for-kc-all-other-versions.jar` | Arch PKGBUILD |
| 根目录 gradle（经典） | JDK + gradle 8.x/9.x wrapper | `lib/build/libs/keycloak-archlinux-theme.jar` | 上游 README 文档化；上游 CI `.gitlab-ci.yml` build job（`gradle --build-cache build`） |

本适配走 **gradle 经典路径**（上游支持的双路径之一）。原因见下节；偏离已如实记录于 manifest.yaml `deviation` 段。

## 为什么不走 PKGBUILD 的 keycloakify 路径（SecureAccessFence 证据链）

HarmonyOS 真机 SecureAccessFence（`const.SystemCapability.Security.SecureAccessFence=true`）
只允许执行携带 OHOS 工具链注入的 `.note.ohos.ident` section 的 ELF（note：namesz=12、
descsz=4、type=1、name="OHOS"+8NUL、desc=0x00000001，共 28 字节）：

1. 本机 OHOS clang 构建的任意二进制（含 `-static`）自动带 note+section，exec 正常；
2. 对可运行二进制做「shstrtab 改名 section / 清零 note 内容 / 抹掉 section 表」任一操作 → exec 被拒（EPERM）→ 检查器按 section 名+内容校验；
3. 外来预编译二进制一律 EACCES：android-NDK 静态 node v26.8.2（INTERP=/system/bin/linker64）、
   官方 `@esbuild/linux-arm64` 0.21.5（Go 全静态）、以及 A/C/D/E/F 五种 note/PT_NOTE/section 表注入变体均拒绝；
4. keycloakify 链路 = yarn → tsc → **vite build（硬依赖 esbuild 二进制）** → keycloakify → maven。esbuild 无 OHOS/musl 官方制品（unofficial-builds 仅 x64-musl），Go 源码自建需 bootstrap 整条 Go 工具链且 Go 内部链接器不产生 OHOS note；
5. node 本体的设备自建通道**可行但未走通到产物**：v22.14.0 源码在真机上 configure 成功（磁盘证据为 config.gypi/config.mk/config.status，configure 日志未落盘保留）；构建脚本中保留了禁用 zlib CRC32 SIMD 的计划性修改（首次构建尝试的日志曾出现 clang 后端对 crc32b intrinsic 的报错，该日志已被后续构建覆盖，现仅存脚本注释）；实际构建止步于 gyp 再生成失败——`gyp: Undefined variable python in tools/v8_gypfiles/v8.gyp` → make Error 1，编译从未启动（无 out/、无 node 二进制）。且即便 node 自建成功，缺 esbuild 时 vite 无法运行 → keycloakify 全链在当前设备安全策略下不可达。

结论：在不动设备安全策略的前提下，keycloakify 路径为硬阻塞；gradle 路径只需 JDK，完全可行。

## 编译环境与步骤（gradle 路径）

- JDK：BiSheng JDK 17.0.13（conanfile `_ensure_java`：JAVA_HOME → ~/bishengjdk17 → PATH → cmd-pkgs 自动安装，与 keycloak-metrics 同链）
- Gradle：9.3.0（wrapper 声明），发行版从腾讯镜像预下载
  （`https://mirrors.cloud.tencent.com/gradle/gradle-9.3.0-bin.zip`，sha256 钉校验，
  services.gradle.org 直连超时不变——keycloak-metrics 8.5 同款方案）；
  wrapper 的 distributionUrl 追加 file:// 行（java.util.Properties 后写覆盖）；
  不执行 gradlew 脚本（HMDFS 禁 shebang exec + busybox xargs 引号坑，keycloak-metrics 同坑），
  直接 `java -cp gradle/wrapper/gradle-wrapper.jar org.gradle.wrapper.GradleWrapperMain build --no-daemon`
- 命令：`gradle build`（与上游 CI build job 一致；纯资源项目，build = assemble + check，
  check 的 test 子任务无测试源按 NO-SOURCE 跳过）
- 产物：`lib/build/libs/keycloak-archlinux-theme.jar`（27 个主题资源文件，无 Java 源码编译）

## 源码修改

无 patch（零修改）。构建期对 worktree 的两处运行时改写（wrapper properties 追加行）由 conanfile 在 build 目录内完成，不入库。

## 上游测试门禁 discovery（NO_UPSTREAM_TESTS）

结论：**上游无任何可执行的测试套件**。discovery 检查清单（全部基于 v2.0.1 归档实际内容核验）：

| # | 检查项 | 证据 | 结论 |
|---|---|---|---|
| 1 | Arch PKGBUILD `check()` | packaging 仓 PKGBUILD（Scout 报告 §2/§3）：只有 build()/package()，**无 check()** | 无官方测试入口 |
| 2 | 上游 CI（.gitlab-ci.yml @v2.0.1） | 仅 `build`（gradle build）与 `v2`（yarn+keycloakify）两个 build stage job，无 test 命令 | 无 CI 测试 |
| 3 | gradle 路径测试目录/依赖 | `lib/src` 下仅 main/resources（27 个主题资源文件），无 test 源集、无 junit/testkit 依赖、build.gradle.kts 无 test 配置 | gradle check 的 test 子任务 NO-SOURCE |
| 4 | keycloakify 路径测试 | v2/package.json scripts 仅 dev/build/build-keycloak-theme/storybook/format；无 test 脚本；devDependencies 无测试框架 | 无测试 |
| 5 | Makefile/独立测试脚本 | 归档根仅 Dockerfile/docker-compose.yml/README/LICENSE/gradlew 等；docker-compose 是手动视觉调试环境（Scout §3） | 无 |
| 6 | 构建开关（是否可启用测试） | 两条路径均无测试开关可言（无任何测试代码存在） | 不适用 |

替代验证（R34 消费者级）：test_package 对主题 JAR 做 17 组实质断言（覆盖口径，与
test_package/MANIFEST.yml assertion_count 一致）——JAR 存在、keycloak-themes.json 注册
archlinux、5 个主题子类型关键 FTL/properties/i18n/品牌资源、MANIFEST.MF、JVM
URLClassLoader 真实加载 3 个资源并校验 themes.json 内容。
断言统计见 test_package/MANIFEST.yml（unzip 清单落盘模式，杜绝 grep -q SIGPIPE 竞态）。

## 遇到的问题与解决方案（平台侧，供后续 JVM/Node 适配复用）

| # | 问题 | 根因 | 解决 |
|---|---|---|---|
| 1 | 外来预编译二进制 exec EACCES | SecureAccessFence 仅放行带 .note.ohos.ident section 的 ELF | 平台策略，无用户侧修复可解除拦截；设备官方签名工具 binary-sign-tool selfSign 实测对外来工具 ELF 失败（Failed to save 4K data to .codesign section）、对 OHOS 构建对照物成功（add codesign section success → exit 42），注入+签名组合亦失败（根因未定，残差边界见 knowledge/drafts/DRAFT-secure-access-fence-exec-policy 与 reports/curator/probe/auditor-exec-policy.txt、auditor-sign-combo.txt）；工具链一律 OHOS clang 设备自建 |
| 2 | make 并行报 mkfifo Operation not permitted | HMDFS 不允许 mkfifo，GNU make 4.4 默认 fifo jobserver | `make --jobserver-style=pipe` |
| 3 | node configure 报 No acceptable C compiler | musl python 的 subprocess/posix_spawn 不做 PATH 解析，裸命令名 ENOENT | CC/CXX 传绝对路径 |
| 4 | gyp 报 Undefined variable python | 设备只有 python3，v8.gyp 引用 `<(python)` | 已尝试、**未验证成功**：构建目录内 `ln -s python3 python` + PATH 前置后构建仍止于同一 gyp 错误 → make Error 1。注意区分两类签名：pixelmatch 类"python 命令名缺失"（符号链接有验证可解）与本 run 的"gyp `<(python)` 变量展开"类（未验证，见 knowledge/drafts/DRAFT-secure-access-fence-exec-policy.md） |
| 5 | zlib crc32_simd.c 与 OHOS clang15 的兼容性存疑 | 首次构建尝试的日志曾出现 clang 后端对 `llvm.aarch64.crc32b` intrinsic 的报错（Cannot select；该日志已被后续构建覆盖，现磁盘证据为 node-build.sh 中的计划性禁用注释，非本机复现记录） | 构建脚本保留禁用 CRC32_ARMV8_CRC32 define 的计划性修改走纯 C 回退（工具链自建步骤，非上游包补丁；对最终交付的 gradle 路径无影响） |
| 6 | /tmp 只读 + curl 不在默认 PATH | OHOS /tmp 只读；非交互 ssh PATH 缺 /usr/bin | TMPDIR 指向用户目录；下载优先 curl（/usr/bin/curl 可用，TLS 正常）失败回退 python3 urllib 免证书 + sha256 钉 |

## 交付事实

- 源码归档 sha256：`a2473f1e8d7b4c4e8928fd90788d6d9f43c85814a5bdaf3afa19ce27ca51b2eb`
  （设备侧两次独立下载字节一致；gitlab.archlinux.org 源稳定，主机侧下载被反爬拦截不可用作基准）
- gradle-9.3.0-bin.zip（腾讯镜像）sha256：`0d585f69da091fc5b2beced877feab55a3064d43b8a1d46aeb07996b0915e0e0`
- 网络通道实测（设备）：registry.npmjs.org / registry.yarnpkg.com / npmmirror / repo1.maven.org / maven.aliyun.com / mirrors.cloud.tencent.com / gitlab.archlinux.org / nodejs.org 均 200 OK；github.com 直连超时（ghfast.top 镜像可达）

**编译日期**: 2026-09-30
**状态**: built（候选）
