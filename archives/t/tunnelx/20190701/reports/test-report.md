# tunnelx 20190701 测试报告

> **项目**: tunnelx（Tunnel / TunnelX）20190701
> **测试日期**: 2026-10-04
> **测试环境**: HarmonyOS / HongMeng Kernel 1.12.0 aarch64（BiSheng OpenJDK 17.0.13，musl）
> **测试类型**: 上游测试入口核验 + 消费者侧验证（Conan L1 test_package）

---

## 一、测试摘要

### 1.1 上游测试入口核验（真实执行）

| 指标 | 数值 | 说明 |
|:----:|:----:|------|
| 上游自动化用例总数 | **0** | 树内无 JUnit / 无 test 源文件 / 无 `make check` / 无 ctest / 无 pytest / 无 autopkgtest |
| 上游可执行入口 | 1 | `Tunnel.MainBox.main`（`src/MainBox.java:596`，AWT/Swing GUI） |
| 入口实际执行 | 是 | `java -cp build/tunnelx.jar Tunnel.MainBox --quiet` → 执行至 `MainBox.java:423` JFrame 构造，因无显示后端抛 `HeadlessException`（栈帧含 `Tunnel.MainBox.main`），进程 rc=1 |
| 通过 / 失败 / 跳过 | — | 上游无自动化用例，无"通过率"可统计（如实申报 0/0，不以后者替代） |

> 说明：上游未提供任何自动化测试，因此不存在"漏测"的形式化基线；本节据用户
> 要求"展示真实测试入口或明确说明没有测试入口"如实登记唯一入口与其实际执行结果。

### 1.2 新增消费者测试（test_package，不并入上游统计）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总检查数 | 11 | 100% |
| 通过 (PASS) | 11 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 鸿蒙探针断言数 | 7 | 100% |
| 其中鸿蒙特有断言 | 2（OHOS-1 / OHOS-2） | — |
| 探针通过 | 7 | 100% |
| 探针失败 | 0 | 0% |

**消费者侧通过率**: ✅ **18/18 = 100%**

---

## 二、测试结论

### 2.1 总体评价

✅ **包结构、构建产物、JAR 内容、类加载器资源查找、鸿蒙启动器与鸿蒙平台适配全部通过**。
唯一限制为平台/JDK 层：BiSheng OpenJDK 17 未构建 AWT 的 X11 后端
（只有 `libawt.so` + `libawt_headless.so`，无 `libawt_xawt.so`），Swing 窗口无法显示。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无 AWT 图形后端（平台/JDK 限制） | 仅 GUI 交互；编译/打包/类加载/几何内核不受影响 | 🟡 |

### 2.3 可用功能清单

```
✅ 源码构建: javac 81 个源文件 → 230 个 .class，rc=0
✅ 打包: jar cfe → tunnelx.jar（623,817 bytes，Main-Class: Tunnel.MainBox）
✅ 类加载器资源解析: symbols/listdir.txt(38) / tutorials/listdir.txt(8) / symbols/helpfile.md(382 行)
✅ 上游几何内核: Tunnel.Vec3d 运算断言通过
✅ 鸿蒙启动器: bin/tunnelx 自动定位 BiSheng JDK 并拉起 Tunnel.MainBox
✅ 启动器 CLI 契约: bin/tunnelx --version/--help 均 exit 0（CI 平台功能矩阵 L2 = pass）
✅ 鸿蒙临时目录适配: java.io.tmpdir 已重定向出只读 /tmp
⚠️ Swing GUI: 平台无 X11 后端，无法建窗（HeadlessException）
```

### 2.4 已知限制

1. BiSheng OpenJDK 17.0.13（OHOS）仅含 headless AWT，Tunnel 的 Swing 界面在
   OHOS PC 上不可显示；该限制在 `test.sh` T4 中以"入口可达 + 停在 AWT 初始化"如实断言。
2. 运行期可选外部程序 `cavern`/`3dtopos`/`aven`（survex）与 `gdal_translate`（GDAL）
   未随包提供，相关功能为上游运行时门控（`src/FileAbstraction.java:1118/1135/1198/1154-1186`）。

---

## 三、测试详情

### 3.1 通过的测试

测试命令（由 `conan create` 自动调用）：

```bash
JAVA_HOME=<bishengjdk17> /data/service/hnp/bin/bash \
  archives/t/tunnelx/20190701/test_package/test.sh \
  /storage/Users/currentUser/.conan2/p/b/tunne4abc406d96c8d/p
```

| # | 测试项 | 功能 | 结果 |
|---|--------|------|------|
| T1 | `lib/tunnelx.jar` 存在（623,817 bytes） | 包布局 | ✅ PASS |
| T1b | `bin/tunnelx` 启动器存在且可执行 | 包布局 | ✅ PASS |
| T2 | JAR 清单 `Main-Class: Tunnel.MainBox` | 可执行入口声明 | ✅ PASS |
| T3 | `Tunnel/*.class` = 230（≥230） | 打包完整性 | ✅ PASS |
| T3b | 资源 `symbols/listdir.txt` 已打包 | 自包含资源 | ✅ PASS |
| T3b | 资源 `tutorials/listdir.txt` 已打包 | 自包含资源 | ✅ PASS |
| T3b | 资源 `symbols/helpfile.md` 已打包 | 自包含资源 | ✅ PASS |
| T4 | 上游入口 `Tunnel.MainBox` 可达并执行至 AWT 初始化 | 上游入口核验 | ✅ PASS |
| T5 | `bin/tunnelx`（清空 JAVA_HOME）自动定位 JDK 并拉起 `Tunnel.MainBox` | **鸿蒙启动器** | ✅ PASS |
| T5b | `bin/tunnelx --version/--help` 均 exit 0（同 CI L2 smoke test 口径） | **启动器 CLI 契约** | ✅ PASS |
| T6 | 鸿蒙探针 7/7（见 3.2） | 平台+包内容 | ✅ PASS |

鸿蒙探针（`TunnelOhosProbe`，package `Tunnel`，与上游同为包级私有）：

| # | 断言 | 内容 | 结果 |
|---|------|------|------|
| **OHOS-1** | **鸿蒙 aarch64 JVM** | `os.name=HarmonyOS, os.arch=aarch64, java.home=~/bishengjdk17` | ✅ PASS |
| **OHOS-2** | **`java.io.tmpdir` 已离开只读 `/tmp`** | `java.io.tmpdir=/storage/Users/currentUser/tmp` | ✅ PASS |
| PKG-1 | 上游版本标记 | `TN.tunnelversion=version2019-07-01 DoES` | ✅ PASS |
| PKG-2 | `symbols/listdir.txt` | entries=38（37 symbol + listdir.txt 自身，同上游 `jmake` 行为） | ✅ PASS |
| PKG-3 | `tutorials/listdir.txt` | entries=8（7 tutorial + listdir.txt 自身） | ✅ PASS |
| PKG-4 | `symbols/helpfile.md` | 382 行 | ✅ PASS |
| PKG-5 | 上游几何内核 `Vec3d` | `(1,2,3)+(0.5,0.25,-1)*2 = 3.0 4.5 4.0` | ✅ PASS |

OHOS-2 反向验证（阴性对照，证明断言有效）：

```
$ java -Djava.io.tmpdir=/tmp -cp tunnelx.jar:<classes> Tunnel.TunnelOhosProbe
PROBE FAIL OHOS-2 | java.io.tmpdir redirected away from read-only /tmp | java.io.tmpdir=/tmp
PROBE SUMMARY passed=6 failed=1 failed_ids=[OHOS-2]
```

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| （无） | — | 11/11 + 探针 7/7 全通过 |

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| （无） | 上游 0 个自动化用例可跳过；本包新增检查全部执行 |

---

## 四、关键问题分析

### 问题 1: `conan create` 首个错误 —— `get() got an unexpected keyword argument 'tar_format'`

**现象**：

```
ERROR: tunnelx/20190701: Error in source() method, line 94
	get(self, **self.conan_data["sources"]["20190701"], strip_root=True)
	TypeError: get() got an unexpected keyword argument 'tar_format'
```

**根因分析**：`conandata.yml` 的 `tar_format` 属归档规范字段（供校验/索引），
而 `conan.tools.files.get()` 只接受 `url/sha256/destination/strip_root/verify`。

**解决方案**：`source()` 中复制字典并剔除 `tar_format` 后再调用 `get()`，
与 `archives/m/motif`、`archives/a/accountanservice` 等既有配方同一处理。

**重新验证**：`conan create` rc=0，`Package '6b129b06...' created`。

### 问题 2: 工作树检出 `No space left on device`（inode 耗尽）

**现象**：

```
$ git worktree add -b feat/tunnelx-20190701 <path> origin/main
error: unable to create file archives/c/cgreen/1.6.4/notes.md
fatal: cannot create directory at 'archives/c/cgreen/1.6.4/patches'
$ df -i
/…/non_account  48455677 48409860 45817 100%
```

**根因分析**：工作区所在文件系统 inode 已用满（剩余 <6 千），全量检出
（88,718 个受版本控制文件）不可能完成。

**解决方案**：稀疏工作树——`git worktree add --no-checkout` +
`git sparse-checkout set scripts ci templates .gitcode knowledge/{graph,doc,operations,requirements} archives/t/tunnelx`；
检出文件 7,239 → 1,280，释放约 1.2 万 inode。

**重新验证**：工作树可用，`git add archives/t/tunnelx/...`（该目录在稀疏集内）rc=0。

### 问题 3: HarmonyOS 无 AWT 图形后端

**现象**：

```
Exception in thread "main" java.awt.HeadlessException:
No X11 DISPLAY variable was set, ...
	at Tunnel.MainBox.<init>(MainBox.java:423)
	at Tunnel.MainBox.main(MainBox.java:637)
```

**根因分析**：`$JAVA_HOME/lib` 只有 `libawt.so`、`libawt_headless.so`，
缺 `libawt_xawt.so`（BiSheng JDK 未构建 X11 后端），且无 `DISPLAY`。

**解决方案**：属平台限制，不修改上游源码；`test.sh` T4 改为断言
"入口可达 + 执行至 AWT 初始化 + 栈帧含 `Tunnel.MainBox.main`"，
以真实证据证明入口装配正确。

---

## 五、测试环境

```
OS:        HarmonyOS / HongMeng Kernel 1.12.0 aarch64 (Toybox)
JDK:       openjdk version "17.0.13" 2024-10-15
           OpenJDK Runtime Environment BiSheng (build 17.0.13+6)
           OpenJDK 64-Bit Server VM BiSheng (build 17.0.13+6, mixed mode)
Conan:     2.29.1（OHOS 适配版）
Profile:   ci/conan/profiles/ohos-aarch64
           os=OHOS / os.version=6.0 / arch=armv8 / clang 15 / libc++ / cppstd=17 / Release
源码:      https://github.com/goatchurchprime/tunnelx/archive/refs/tags/R2019a.tar.gz
           sha256 de8fbee92325233ccab703a5661b8e119b8bbb710660b7f590454eba82240cfd
包引用:    tunnelx/20190701@ohpcd/stable#24d386016375073c6af1c4f1fe4b90aa
           :6b129b068851896169fae42d399fa922d239ce8a#e9eec8691d89239ec98c3361a67b56bb
```

---

*报告生成时间: 2026-10-04*
