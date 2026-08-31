# alloy-analyzer 6.2.0 适配笔记

## 编译环境
- 构建系统: custom（bnd/Gradle 工作区，Gradle 7.2 via wrapper，JDK 17 源码构建）
- 编译日期: 2026-08-30
- 运行时/构建工具: bishengjdk 17.0.13（cmd-pkgs install-jdk.sh 安装，自签名）+ Gradle 7.2
- 状态: built（本地 conan create 验证通过，上游 25/25 JUnit 测试全通过）

## 编译步骤

1. **获取上游源码**（官方 GitHub v6.2.0，R39；CI 对 github.com 自动注入 gh-proxy 镜像）:
   ```bash
   # https://github.com/AlloyTools/org.alloytools.alloy/archive/refs/tags/v6.2.0.tar.gz
   # SHA256: 59ef434a54a0f8ab82fdc18ad2287f2ffbce2a7c29b84208a5e73be40e926246 (14.5MB)
   ```

2. **配置构建环境**（conanfile.py build() 自动处理）:
   - 探测/安装 bishengjdk 17（`~/bishengjdk17` 或 cmd-pkgs install-jdk.sh 自动安装）
   - `JAVA_TOOL_OPTIONS=-Dos.name=Linux`：Gradle/kodkod 不识别 HarmonyOS os.name，统一别名 Linux
   - `GRADLE_USER_HOME`/`TMPDIR` 指向可写目录（OHOS /tmp 只读，E002）
   - gradle-wrapper.properties 的 services.gradle.org 改为 mirrors.cloud.tencent.com（国内可达，ktfmt 先例）

3. **构建 + 上游测试**: `gradle build`（直接 java -cp gradle-wrapper.jar 调用，绕过 toybox 无法运行的 gradlew 脚本）
   - 编译全部模块（application/core/cli/dist/extra/lsp/wrappers/api/pardinus）
   - **运行上游 JUnit 测试：25 个用例全部通过（0 失败 0 错误 0 跳过）**
     - application: FindReplaceTest(1) + InternalTest(6)
     - core: PosTest(3) + AlloyModelsTest(3) + CanvasTest(5) + TableTest(7)
   - 产出 dist jar：`org.alloytools.alloy.dist/target/org.alloytools.alloy.dist.jar`（~17.7MB）

4. **打包**: dist jar → `libexec/`，生成 HarmonyOS 适配版 `bin/alloy` wrapper

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 直连超时 | 本机/CI 网络无法直连 GitHub | conandata.yml 用官方 GitHub URL，CI 自动 gh-proxy 镜像 fallback；本地用 gh-proxy 验证 |
| 2 | 系统 JDK（/data/service/hnp bishengjdk8）无法启动 | 沙箱内 JVM 无法预留 code cache | 用 cmd-pkgs `install-jdk.sh` 安装自签名 bishengjdk 17.0.13 |
| 3 | gradle wrapper 下载 gradle-7.2 超时 | services.gradle.org 不可达 | distributionUrl 改 mirrors.cloud.tencent.com/gradle |
| 4 | gradlew shell 脚本无法运行 | OHOS /bin/sh 为 toybox，缺少脚本特性 | 直接 `java -cp gradle-wrapper.jar org.gradle.wrapper.GradleWrapperMain` 调用 |
| 5 | Gradle 报 ExceptionInInitializerError / kodkod 平台不识别 | HarmonyOS os.name 不被 Gradle/kodkod 识别 | `JAVA_TOOL_OPTIONS=-Dos.name=Linux` 对所有 JVM 进程生效 |
| 6 | /tmp 只读 | OHOS /tmp 只读文件系统（E002） | GRADLE_USER_HOME/TMPDIR 指向可写目录 |
| 7 | bnd 测试报告在 build/ 找不到 | bnd 工作区输出目录为 target/ 非 build/ | 测试报告位于各模块 `target/test-reports/test/*.xml` |

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| bishengjdk | 17.0.13 | JDK（构建 + 运行时） |
| gradle | 7.2 | 构建工具（wrapper 分发） |

## 验证结果

```bash
# 上游测试（gradle build 内运行）：25/25 通过
#   application: FindReplaceTest(1)+InternalTest(6)=7  core: PosTest(3)+AlloyModelsTest(3)+CanvasTest(5)+TableTest(7)=18

# alloy version
$ alloy version
6.2.0

# alloy exec hello.als（真实求解）
$ alloy exec hello.als
00. run   show                     0    1/1     SAT
# 生成 hello/receipt.json 与 hello/show-solution-0.md
```

## 交付物

| 文件 | 说明 |
|------|------|
| `libexec/org.alloytools.alloy.dist.jar` | 源码构建的 Alloy 6.2.0 自包含 JAR（~17.7MB） |
| `bin/alloy` | HarmonyOS 适配版 wrapper，调用 `java -jar` |

## 注意事项

- alloy-analyzer 是 JVM 应用，conan 配方理论上只需 os+arch；但本仓库 CI L0p 门禁要求
  settings 四项齐全（os/compiler/build_type/arch），故本配方声明全部四项（构建不使用 compiler）
- 构建需 JDK 17（bishengjdk，conanfile 自动探测/安装）；运行时 wrapper 自动探测
- 上游测试在 `gradle build` 阶段执行，25/25 通过；任何测试失败都会使 conan create 失败
- 时间逻辑模型校验（Electrod 后端）需用户自装 NuSMV/nuXmv（可选）
