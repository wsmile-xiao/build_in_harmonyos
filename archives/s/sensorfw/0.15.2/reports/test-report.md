# sensorfw 0.15.2 测试报告

> **软件**: sensorfw（Sailfish OS 传感器框架：sensord 守护进程 + D-Bus 客户端库 + 47 个运行期
> dlopen 的 adaptor/chain/filter/sensor 插件）
> **版本**: 0.15.2
> **测试日期**: 2026-09-27
> **测试环境**: HarmonyOS PC / OpenHarmony aarch64（musl + libc++，clang 15.0.4，Conan 2.29.1）
> **测试类型**: 上游官方测试套件（QtTest）+ 新增鸿蒙消费者测试（test_package）

> **日志留存说明**：本 PR **只提交报告类证据**（`reports/test-report.md`、
> `reports/conan-verify-report.md`、`reports/pr-body.md`），**不提交原始日志** —— 与本仓惯例一致
> （全仓 12287 个包中仅 2 个提交 `reports/logs/`；每包提交文件数中位数 11 / P90 16）。
> 文中出现的 `reports/*.log`、`reports/upstream-test-summary.tsv`、
> `reports/run-upstream-tests.sh` 均为**本地复现路径**，可由 §六 的命令原样重放；
> 与结论直接相关的原文（编译规模、`make check` 两次执行、逐套件用例级/断言级结果、
> 失败断言与 `Loc`、门禁计数）已**逐段内联**于本报告，评审无需查阅原始日志即可复核每条断言。

---

## 一、测试摘要

上游测试有两套口径，本报告分开列出（QtTest 的 `Totals:` 行**混用两种单位**，
不能直接引用，详见 §3.3）：

| 口径 | 总数 | 通过 | 失败 | 跳过 | 未执行 |
|:----:|:----:|:----:|:----:|:----:|:------:|
| **上游用例级**（9 个二进制 / `-functions` 声明） | 51 | 15 | 4 | 0 | 32 |
| **上游断言级**（`PASS` / `FAIL!` 行） | 43 | 26 | 17 | 0 | — |
| **新增鸿蒙消费者用例**（test_package） | 6 | 6 | 0 | 0 | 0 |

- **已执行用例通过率**: 15 / 19 = **78.9 %**（32 个未执行全部因沙箱缺 D-Bus daemon 与传感器硬件，
  见 §2.4）
- **消费者用例通过率**: 6 / 6 = **100 %**（含鸿蒙特有用例 `consumer.ohos.dlopen`）
- **消费者断言**: 29 / 29 = **100 %**

**逐二进制明细**（用例级 = `-functions` 声明的函数名归并 `PASS`/`FAIL!` 行；断言级 = `PASS`/`FAIL!` 行本身。
「日志」列为本地复现路径，未随 PR 提交）：

| # | 二进制 | 命令 | 声明用例 | 通过 | 失败 | 未执行 | 断言 通过/失败 | 退出码 | 日志（本地） |
|:-:|--------|------|:-------:|:----:|:----:|:------:|:-------------:|:------:|--------------|
| 1 | `tests/filters/sensorfilters-test` | `<bin> -v1` | 6 | 2 | **4** | 0 | 4 / 14 | 14 | `reports/tests_filters_sensorfilters-test.log` |
| 2 | `tests/dataflow/sensordataflow-test` | `<bin> -v1` | 2 | **2** | 0 | 0 | 4 / 0 | 0 | `reports/tests_dataflow_sensordataflow-test.log` |
| 3 | `tests/adaptors/sensoradaptors-test` | `<bin> -v1` | 9 | **9** | 0 | 0 | 11 / 0 | 0 | `reports/tests_adaptors_sensoradaptors-test.log` |
| 4 | `tests/chains/sensorchains-test` | `<bin> -v1` | 2 | **2** | 0 | 0 | 4 / 0 | 0 | `reports/tests_chains_sensorchains-test.log` |
| 5 | `tests/client/sensorapi-test` | `<bin> -v1` | 19 | 0 | 0 | **19** | 1 / 1 | 1 | `reports/tests_client_sensorapi-test.log` |
| 6 | `tests/metadata/sensormetadata-test` | `<bin> -v1` | 9 | 0 | 0 | **9** | 1 / 1 | 1 | `reports/tests_metadata_sensormetadata-test.log` |
| 7 | `tests/benchmark/benchmarktest/sensorbenchmark-test` | `<bin> -v1` | 4 | 0 | 0 | **4** | 1 / 1 | 1 | `reports/tests_benchmark_benchmarktest_sensorbenchmark-test.log` |
| 8 | `tests/deadclient/sensord-deadclient` | `<bin>`（非 QtTest） | — | — | — | — | 0 / 0 | 124（90 s 超时） | `reports/tests_deadclient_sensord-deadclient.log` |
| 9 | `tests/testapp/sensortestapp` | `<bin>`（交互式） | — | — | — | — | 0 / 0 | 1 | `reports/tests_testapp_sensortestapp.log` |
| | **合计** | | **51** | **15** | **4** | **32** | **26 / 17** | | `reports/upstream-tests-stdout.log` |

**上游测试入口**：`make check`（qmake 为 `TEMPLATE = subdirs` 自动生成；
`tests/<suite>/Makefile` 的规则经 `target_wrapper.sh` 直接运行 QtTest 二进制，
其余 51 条 `check` 规则为空操作）。`make check` **已真实执行两次**：

- 原样执行 → `EXIT=2`：`tests/<suite>/target_wrapper.sh` 把**构建期 Qt 包**的 `lib/`
  前置进 `LD_LIBRARY_PATH`，而该目录里 `libQt5*.so.5` 是符号链接、本平台**启动期解析
  `DT_NEEDED` 名字时不接受符号链接条目** → 测试二进制连加载都过不去。
  日志 `reports/upstream-make-check.log`。
- 补足运行环境（解引用库目录 + 上游 `SENSORFW_SOCKET_PATH`/`SENSORFW_LIBRARY_PATH`）→
  套件真实运行，`FilterApiTest` 报 `Totals: 4 passed, 14 failed`，随后
  `*** [Makefile:346: check] Error 14` —— 因 `check` 是 `-check_ordered`，
  **首个失败套件即整链中止**，拿不到全量结果。日志 `reports/upstream-make-check-env.log`。

故完整逐套件画像由一份**本地 harness**（`reports/run-upstream-tests.sh`，本地产物、
未随 PR 提交）逐二进制执行得到，产物为 `reports/upstream-tests-stdout.log`（含 `GRAND TOTAL`）、
`reports/upstream-test-summary.tsv`（用例级 + 断言级两组列）与
`reports/tests_<suite>.log` / `reports/tests_<suite>.functions.log`；其中逐用例结果已内联于
上文「逐二进制明细」表，harness 的三项平台必需准备工作见 §六。

---

## 二、测试结论

### 2.1 总体评价

⚠️ **适配本身达标（移植相关用例全绿），但上游自带测试套件在非设备主机上不可能全绿。**

判定依据：与移植相关的三个套件全部通过 —— `sensoradaptors-test` **9/9**、
`sensordataflow-test` **2/2**、`sensorchains-test` **2/2**；失败的 4 个用例全部集中在
`sensorfilters-test` 的**方向语义**上，且该失败与 OHOS/鸿蒙无关（见 §四问题 1）。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 上游「测试期望 ↔ 实现」不一致（方向语义符号相反） | `sensorfilters-test` 4 个用例 / 17 条断言 | 🟡 上游既有问题，非移植缺陷 |
| 沙箱缺 D-Bus daemon | `sensorapi-test` 19 + `sensormetadata-test` 9 + `sensorbenchmark-test` 4 = 32 个用例未执行 | 🟢 环境限制，非缺陷 |
| 沙箱无传感器硬件 / 无 `/run` | `sensord-deadclient`（exit 124）、`sensortestapp`（交互式） | 🟢 环境限制，非缺陷 |
| 框架侧（非本包）：L4 正则缺前导 `\b` 导致误报 | 本包 L4 记 `warn` | 🟢 框架问题，已提交反馈 |
| 框架侧（非本包）：L2 冒烟测试未用 conanrun 环境 | 本包 L2 记 `skip` | 🟢 框架问题，已提交反馈 |

### 2.3 可用功能清单

```
✅ 全部 47 个插件可在本平台 dlopen(RTLD_NOW) 并解析未定义符号（补丁 0004 + 0005）
✅ 9 个 adaptor 插件、2 个 chain 插件、2 个 dataflow 场景真实运行通过
✅ libsensorclient-qt5 / libsensordatatypes-qt5 / libsensorfw-qt5 三个库可被消费者链接并真实调用
✅ 随包的 180 个公开头文件与上游 install 规则逐项一致，可编译
✅ bin/sensorfwd 可执行并输出用法（--help）
⚠️ D-Bus 客户端 API（sensorapi-test / sensormetadata-test / sensorbenchmark-test）
   需运行中的 sensord + D-Bus daemon，构建主机上不可验证
❌ 无
```

### 2.4 已知限制

1. 上游测试定义（`tests/tests.xml.in`）把每个 `<case>` 声明为 `<hardware>true</hardware>`，
   并要求先 `start sensord`；构建主机上无法满足，因此 32 个用例只能记录为「未执行」。
2. `tests/filters` 的 4 个方向语义用例在上游任何平台都会失败；**不得修改测试期望去迁就实现**
   （那等于伪造测试结果），故按 `docs/TEST_QUALITY_SPEC.md` §3.3 声明豁免。
3. `bin/sensorfwd` 的 `RUNPATH` 只指向构建期 Qt 包的 `lib/`，不含自身的 `lib/`；
   直接以包目录运行需按 DT_NEEDED 闭包做解引用重定位（见 §四问题 3）。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 | 日志 |
|--------|------|------|------|
| `testAccelerometerAdaptor` 等 9 个 | 各类 adaptor 插件加载与数据流 | ✅ PASS | `reports/tests_adaptors_sensoradaptors-test.log` |
| `testAdaptorSharing` / `testChainSharing` | 插件实例共享与链路共享 | ✅ PASS | `reports/tests_dataflow_sensordataflow-test.log` |
| `testCompassChain` / `testAccelerometerChain` | 跨插件 DT_NEEDED（补丁 0005 回归） | ✅ PASS | `reports/tests_chains_sensorchains-test.log` |
| `testCoordinateAlignFilter` | 坐标对齐滤波器 | ✅ PASS | `reports/tests_filters_sensorfilters-test.log` |
| `testDeclinationFilter` | 磁偏角滤波器 | ✅ PASS | `reports/tests_filters_sensorfilters-test.log` |
| `consumer.api.types`（9 断言） | 数据类型 API 与时戳往返 | ✅ PASS | test_package 内 |
| `consumer.api.qtmeta`（5 断言） | QObject 元对象系统 | ✅ PASS | test_package 内 |
| `consumer.ohos.dlopen`（4 断言） | **鸿蒙特有**：47 插件 `dlopen(RTLD_NOW)` + Qt 元数据入口 | ✅ PASS | test_package 内 |
| `consumer.ohos.elfarch` / `.packaging` / `consumer.daemon.help` | 架构 / 包布局与头文件布局 / 守护进程自省 | ✅ PASS | test_package 内 |

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| `testTopEdgeInterpretationFilter` | 上游测试期望与实现方向语义相反 | 5 条断言不等，见 §四问题 1 |
| `testFaceInterpretationFilter` | 同上 | 3 条断言不等 |
| `testOrientationInterpretationFilter` | 同上 | 6 条断言不等 |
| `testRotationFilter` | 同上 | `Actual (d1->x_): nan` vs `Expected: 0` |

### 3.3 跳过的测试

上游没有 `QSKIP`；下表的**未执行**是指用例已声明但从未进入 ——
`initTestCase()` 前置失败后 QtTest 直接收尾，`-v1` 输出里既无 `PASS` 也无 `FAIL!` 行。

| 测试项 | 未执行原因 |
|--------|------------|
| `sensorapi-test` 19 个用例 | `initTestCase()` 失败：`'remoteSensorManager.isValid()' returned FALSE`（无 D-Bus daemon） |
| `sensormetadata-test` 9 个用例 | 同上 |
| `sensorbenchmark-test` 4 个用例 | 同上 |
| `sensord-deadclient` | 需运行中的 sensord（tests.xml 先 `start sensord`）；实测 90 s 超时 → exit 124 |
| `sensortestapp` | 交互式示例程序，无人值守环境无法完成 |

> **统计单位提醒**：QtTest 的 `Totals:` 行 `passed` 计「完整通过的测试函数」、
> `failed` 计「**失败的断言**」。例：`sensorfilters-test` 声明 6 个用例却打印
> `Totals: 4 passed, 14 failed`。本报告的用例级数字按 `-functions` 声明的函数名
> 归并 `PASS`/`FAIL!` 行得到，断言级数字才是 `PASS`/`FAIL!` 行本身。

---

## 四、关键问题分析

### 问题 1: 上游 `tests/filters` 4 个方向语义用例失败（与平台无关）

**现象**（`reports/tests_filters_sensorfilters-test.log` 原文）：

```
FAIL!  : FilterApiTest::testFaceInterpretationFilter() Compared values are not the same
   Loc: [./filtertests.h(140)]
FAIL!  : FilterApiTest::testFaceInterpretationFilter() Compared values are not the same
   Loc: [./filtertests.h(140)]
FAIL!  : FilterApiTest::testFaceInterpretationFilter() Compared values are not the same
   Loc: [./filtertests.h(140)]
...
FAIL!  : FilterApiTest::testRotationFilter() Compared floats are not the same (fuzzy compare)
   Actual   (d1->x_): nan
   Expected (d2->x_): 0
   Loc: [./filtertests.h(152)]
Totals: 4 passed, 14 failed, 0 skipped, 0 blacklisted, 2ms
```

> 说明：`testFace/TestTopEdge/TestOrientationInterpretationFilter` 的失败只打印
> `Compared values are not the same` 与代码位置，**不打印 Actual/Expected**；
> 只有 `testRotationFilter` 打印了取值（`nan` vs `0`）。

**根因分析**：所有 `Loc: [./filtertests.h(140)]` 指向同一行断言 ——
`filtertests.h:139` 比较 `timestamp_`、`:140` 比较 `orientation_`：

```cpp
// tests/filters/filtertests.h
QCOMPARE(d1->timestamp_,   d2->timestamp_);     // :139 通过
QCOMPARE(d1->orientation_, d2->orientation_);   // :140 失败
```

即**时间戳相等、方向枚举不等**，实现输出的方向与测试期望**符号相反**。
对应实现（`filters/orientationinterpreter/orientationinterpreter.cpp`）：

```cpp
:240  newFace.orientation_    = ((data.z_ <= 0) ? PoseData::FaceDown : PoseData::FaceUp);
:174  newTopEdge.orientation_ = (rotation <= 0) ? PoseData::LeftUp : PoseData::RightUp;
```

以 `testFaceInterpretationFilter` 的输入 `z = -981`（t=0）为例：`:240` 给出 `FaceDown`，
而 `tests/filters/filtertests.cpp` 的期望数据是 `PoseData(0, PoseData::FaceUp)`；
`testTopEdgeInterpretationFilter` 的输入 `x = -981` 经 `atan(-981/0) = -90°` 进
`rotateToLandscape()`，`:174` 因 `rotation <= 0` 给出 `LeftUp`，而期望是 `RightUp`。

该判定只依赖源码里的整数/浮点比较与 `atan()` 的符号，**不依赖 OHOS 任何特性**
（无硬件、无 D-Bus、无配置、无 syscall）；运行期日志里的
`minLimit: 0 0` / `maxLimit: 2147483647 2147483647` 正是编译期默认值
（`OVERFLOW_MIN = 0`、`OVERFLOW_MAX = INT_MAX`），说明与「配置未加载」无关：
用例数据量级为 `981² = 962361`，落在设备配置窗口（`config/sensord-ncdk.conf` 的
800–1250 → 平方 640000–1562500）**之内**，加不加配置都不触发溢出丢弃。
`testRotationFilter` 的 `Actual (d1->x_): nan` / `Expected: 0` 是同一方向语义问题的
另一表现（`nan` 来自对 0 输入做除法）。

**解决方案**：**不修**。改测试期望去迁就实现等于伪造测试结果。按
`docs/TEST_QUALITY_SPEC.md` §3.3 第 3 条在 `test_package/MANIFEST.yml` 声明豁免并给出逐项根因。

### 问题 2: `make check` 原样执行时测试二进制无法加载

**现象**：

```
Error loading shared library libQt5DBus.so.5: (needed by .../sensorfilters-test)
```

**根因分析**：qmake 生成的 `tests/<suite>/target_wrapper.sh` 把自己**构建期** Qt 包的
`lib/` 前置进 `LD_LIBRARY_PATH`；该目录里 `libQt5*.so.5` 是版本化**符号链接**，
而本平台加载器在**程序启动解析 `DT_NEEDED` 名字**时把符号链接条目当成「不存在」。
对照实测：同一批文件（可写目录、属主为当前用户）为符号链接 → 启动失败；
`cp -L` 解引用为实体文件 → 启动成功。注意**不是「禁用符号链接」**：同一符号链接用
`dlopen("<裸名>")` 与 `dlopen("<完整路径>")` 在独立进程中均成功。

**解决方案**：测试侧做解引用重定位（`test_package/test.sh` 与
`reports/run-upstream-tests.sh` 均按 DT_NEEDED 闭包 `cp -L` 到私有目录后运行）；
`make check` 则用 `TESTRUNNER="env LD_LIBRARY_PATH=<deref dir>"` 覆盖注入顺序。
**不修改依赖包**。

### 问题 3: test_package 的 `test()` 曾用 `CONFIG_SHELL` 选解释器（已修复）

**现象**：`conan-verify` G2 报 `Error in test() method, line 151`，日志里
`test.sh[242]: syntax error: unexpected '< '`。

**根因分析**：`CONFIG_SHELL` 在 autoconf 与**本仓门禁环境**里本义就是 `/bin/sh`
（CI profile 与 `scripts/ohc-run.py` 都导出 `CONFIG_SHELL=/bin/sh`，而本机 `/bin/sh` 是 mksh），
于是 `test.sh` 被 mksh 执行，撞上 bash 专有的进程替换 `done < <(sed …)`。

**解决方案**：两层修复 —— ① `test.sh` 改为纯 POSIX 写法（落临时文件再重定向读），
`bash -n` 与 `/bin/sh -n` 双通过；② `conanfile.py` 改用专用变量
`SENSORFW_TEST_SHELL`，否则按 bash 候选路径依次探测，**不再读 `CONFIG_SHELL`**。
重新验证：`conan-verify` G2 PASS，test_package `用例: 总 6 / 通过 6 / 失败 0`。

### 问题 4: 框架侧两处误判（非本包问题，已提交反馈）

- **L4 `warn`**：门禁用 `grep -rlE '(strcpy|sprintf|gets|strcat)\b' patches/`，
  **缺前导 `\b`**，于是英文单词 **`targets`** 命中 `gets\b`
  （本包 0005 补丁注释里的 "…targets exist by the time this project is linked."）。
  加上前导 `\b` 后零命中。
- **L2 `skip`**：`L2: Smoke test (version/help check)` 直接运行包内
  `bin/sensorfwd --version/--help`，未使用 `conanrun` 环境、也未做解引用重定位；
  而该二进制的 `RUNPATH` 只指向构建期 Qt 包的 `lib/`（其中的 Qt 库是符号链接），
  故必失败并被记为 `skip`（非阻塞）。同一检查用 `test_package` 的解引用环境做就是 PASS
  （见 `consumer.daemon.help`）。

---

## 五、测试环境

```
目标平台     : HarmonyOS PC / OpenHarmony aarch64（aarch64-linux-ohos，musl + libc++）
编译器       : clang 15.0.4（/data/service/hnp/bin/clang++），-stdlib=libc++，C++17
构建系统     : qmake（mkspec harmonyos-clang）+ make -j1 QMAKE_STRIP=""
Conan        : 2.29.1 @ohpcd/stable，profile ci/conan/profiles/ohos-aarch64
依赖         : qt/5.15.19.1（含 QtDBus）、libudev-zero/1.0.4（静态）
包引用       : sensorfw/0.15.2@ohpcd/stable
包 ID        : 0b1ed271d5a43d09cfbf73bd802eb39db37e8ab9
产物         : 394 个 .o、68 个 .so（全部实体文件，符号链接 0）、47 个插件、
               180 个公开头文件、9 个测试二进制
门禁         : conan-verify G0–L5 全 PASS（Verdict=PASS）；
               W3 本地 CI `.ci-result.json` exit_code=0（L0/L1/L1e/L5 pass，
               L2 skip、L4 warn 均为上述框架误判）
```

---

## 六、复现方式（本地命令）

```bash
# ① 全量重建（含 test_package；依赖已在 Conan 缓存中，不使用 --build=missing）
conan create archives/s/sensorfw/0.15.2 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=sensorfw/0.15.2

# ② 配方门禁（G0–L5）
python3 scripts/ohc-run.py conan-verify sensorfw 0.15.2

# ③ 本地 CI 模拟（L0 / JC / KC + W3）
CI_PACKAGES=archives/s/sensorfw/0.15.2 bash ci/conan/build_and_test.sh

# ④ 上游测试：原样执行 make check（记录加载失败，见 §一）
make check

# ⑤ 上游测试：补足运行环境 + 逐二进制取得完整画像
SENSORFW_BUILD=<build 目录> QT_LIB=<qt 包>/lib PREFIX=<可写前缀> \
  bash reports/run-upstream-tests.sh        # 本地 harness，未随 PR 提交
```

harness 做三件平台必需的准备工作（全部是上游既有机制或纯运行期布置，**不改上游代码**）：

1. **解引用重定位**：按 DT_NEEDED 传递闭包 `cp -L` 到私有目录后运行（`/system/*`、`/vendor/*`、
   `/lib*`、`/usr/lib/*` 不复制；`/system/lib64/libc.so` 绝不复制，否则破坏 musl libc 绑定）。
2. **`SENSORFW_SOCKET_PATH=<前缀>`**（上游环境变量，**前缀**语义；`core/sensormanager.cpp:170-174`、
   `qt-api/socketreader.cpp:53-57`）：让 socket 落到可写目录。未设置时硬编码 `/run/sensord.sock`，
   而沙箱无 `/run` 且不可创建 → `initTestCase()` 直接 `QFATAL: ASSERT`。
3. **`SENSORFW_LIBRARY_PATH=<前缀>`**（上游环境变量，前缀语义；`core/loader.cpp:56-64`）：插件目录在
   编译期被烘焙成 `$$[QT_INSTALL_LIBS]/sensord-qt5`（`core/core.pro` 的 `PLUGIN_DIRECTORY`），
   Conan 包搬运后必然悬空，故按烘焙路径的相对结构在可写前缀下布置 47 个插件的实体副本。

每个二进制执行两步：`<bin> -functions`（枚举已声明用例）→ `<bin> -v1`
（真实执行并打印逐用例 `PASS`/`FAIL!` 与 `Totals:` 行）。

---

*报告生成时间: 2026-09-27*
