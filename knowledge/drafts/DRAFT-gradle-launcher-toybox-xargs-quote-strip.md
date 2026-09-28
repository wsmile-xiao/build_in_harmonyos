# draft-gradle-launcher-toybox-xargs-quote-strip

## 症状

在 OHOS 设备上运行官方 Gradle 发行版的 `bin/gradle`（构建 JVM 项目，或
`gradlew`/发行包内直接调用），无论 `sh` 还是 `bash` 解释，一律立即失败：

```
$ JAVA_HOME=/storage/Users/currentUser/bishengjdk17 sh .../gradle-7.4.2/bin/gradle --version

Error: Could not find or load main class "-Xmx64m"
Caused by: java.lang.ClassNotFoundException: "-Xmx64m"
```

辨别性指纹：**报错的主类名带着字面双引号**（`"-Xmx64m"`）——这是引号未被
剥离残留在参数里的直接证据。

## 根因

Gradle 7.4.2 `bin/gradle` 的 JVM 参数重组管道显式依赖 POSIX xargs 的剥引号
语义，四步机理链（逐行核实）：

1. `bin/gradle` 第 89 行：
   ```sh
   DEFAULT_JVM_OPTS='"-Xmx64m" "-Xms64m"'
   ```
   值内含**字面双引号**。
2. 第 208-233 行用 `printf | xargs -n1 | sed | tr` + `eval set --` 重组 JVM
   参数。脚本注释自述其正确性前提：
   > with -n1 it outputs one arg per line, **with the quotes and backslashes
   > removed**
3. 设备 toybox xargs **不做引号剥离**（GNU xargs 会剥）：
   ```
   $ echo '"-Xmx64m" "-Xms16m"' | xargs -n1 echo
   "-Xmx64m"          ← 引号原样保留（toybox）
   "-Xms16m"
   ```
4. 于是 `eval set --` 后位置参数是带引号的 `'"-Xmx64m"'`，java 把它当主类名
   → `Could not find or load main class "-Xmx64m"` → 构建无法启动。

**归因勘误（重要，勿复制旧记录的"toybox sh"归因）**：坏点在**外部工具
xargs 的引号语义**，而非 shell 解释器。反事实探针：

```
$ /data/service/hnp/bin/bash .../gradle-7.4.2/bin/gradle --version
Error: Could not find or load main class "-Xmx64m"      ← bash 同样失败
```

换 shell、改 PATH、替换 `/bin/sh` 都无效，因为被调用的 `xargs` 二进制不变。

## 修复

绕过 shell 包装，直接以 java 启动 `GradleMain`（classpath 通配符由 java
自身展开，不经 shell/xargs）：

```bash
$JAVA_HOME/bin/java \
  -Dorg.gradle.appname=gradle \
  -classpath "$GRADLE_HOME/lib/*" \
  org.gradle.launcher.GradleMain \
  --no-daemon --console=plain <tasks...>
```

conan 配方中（leakcanary-shark/2.14 实证）：

```python
gradle_cmd = [
    os.path.join(java_home, "bin", "java"),
    "-Dorg.gradle.appname=gradle",
    "-classpath", os.path.join(gradle_home, "lib", "*"),
    "org.gradle.launcher.GradleMain",
    "--no-daemon", "--console=plain",
    ":shark:test", ...,
]
subprocess.Popen(gradle_cmd, ...)   # 列表传参，通配符留给 java 展开
```

配套：`JAVA_TOOL_OPTIONS` 追加 `-Dos.name=Linux`（Gradle 的
OperatingSystem 类不识别 HarmonyOS，会 `ExceptionInInitializerError`；
gradle/8.12 包同款先例）。

**替代方案（分发 Gradle 本身的包适用）**：打包期把 `bin/gradle` 整体重写为
直启 GradleMain 的 wrapper（JAVA_HOME 探测 + os.name 规避 + classpath 拼接
都进 wrapper），见 `archives/g/gradle/8.12/conanfile.py` 的
`_create_wrapper()`。权衡：多一层包装维护面；构建单库时直启更轻。

**不要做**：
- 修补 `bin/gradle` 的引号转义或改 `DEFAULT_JVM_OPTS`——治标，每个 Gradle
  版本都要重做；
- 换 shell / 替换 `/bin/sh`——bash 下同样失败（探针反例）；
- 为单库安装 GNU findutils/xargs——扩大依赖面，CI 不保证提供。

## 验证

自包含探针（新 shell 可跑，不依赖本 run 构建物）：

```bash
# ① 症状复现
JAVA_HOME=/storage/Users/currentUser/bishengjdk17 \
  sh /storage/Users/currentUser/gradle-dist/gradle-7.4.2/bin/gradle --version
# → Error: Could not find or load main class "-Xmx64m"

# ② 机理探针（最小复现）
echo '"-Xmx64m" "-Xms16m"' | xargs -n1 echo
# toybox：输出带引号；GNU xargs：引号已剥

# ③ 反事实探针（坏点在 xargs 而非 shell）
/data/service/hnp/bin/bash /storage/Users/currentUser/gradle-dist/gradle-7.4.2/bin/gradle --version
# → 与 sh 同样失败

# ④ 修复后（直启 GradleMain）
$JAVA_HOME/bin/java -Dorg.gradle.appname=gradle \
  -classpath "/storage/Users/currentUser/gradle-dist/gradle-7.4.2/lib/*" \
  org.gradle.launcher.GradleMain --version
# → Gradle 7.4.2 正常输出版本信息
```

实证：leakcanary-shark 2.14 改直启后，上游 4 模块 172 个 @Test 用例真机
全部通过，权威 CI（ci/conan/build_and_test.sh）全绿（2026-09-26）。

## 适用范围

- 任何在 OHOS 设备上用官方 Gradle 发行版（`bin/gradle`）构建 JVM 项目的
  场景；Gradle 6.x-8.x 启动脚本均含该 xargs 管道，与库无关；
- 依赖 Gradle 源码构建的 JVM 库配方（build() 内调 gradle）；
- 在设备上直接使用 gradle 命令行工具的包（gradle/8.12 类发行包）。

## 关联

- E402（toybox gzip 仅短选项）/ E010（toybox sed/expr）/ E098（toybox 缺
  install）：同属 OHOS toybox 工具能力/语义差异族，本条新增 xargs 引号
  剥离语义这一独立差异点；
- E043（shell 运行时族）：症状同为"脚本跑不起来"，但坏点位置不同
  （shell vs xargs），辨别指纹是报错主类名带字面引号；
- P-BUILD-001（平台限制必须降级而非绕过）：本条的"降级"即绕过 shell 包装
  直接用 java 启动，不做无意义的反复重试或上游脚本修补。
