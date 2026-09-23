# dcled 2.2 — 测试报告

- 软件: dcled 2.2
- 目标平台: ohos-aarch64 (aarch64-linux-ohos)
- 构建系统: makefile（plain make）
- 编译器: clang
- 依赖: libusb/1.0.27
- 测试日期: 2026-09-12
- 结论: **通过**（上游测试 11/11，消费者测试 15/15，conan-verify 全门禁 PASS）

## 一、上游测试（必须全部执行）

### 1.1 上游测试资产清点

dcled 上游**没有自动化测试套件** —— `makefile` 中没有 `check` / `test` 目标，
源码树中也没有测试目录。上游提供的可执行验证面为：

| 来源 | 内容 | 条目数 |
|------|------|--------|
| README `EXAMPLES` 段 | 9 条命令行示例 | 9 |
| README 正文 | `dcled --test` 自检模式 | 1 |
| 构建产物 | `cpuload`（第二个可执行文件，输出负载采样） | 1 |
| **合计** | | **11** |

由于没有 `make check`，上游测试由配方 `conanfile.py` 的 `_run_upstream_checks()`
在 `build()` 阶段直接执行（`-n` 免硬件模式，无需真实 USB 消息板），
结果以 `HMBS_UPSTREAM_TEST_RESULT=` 输出给 CI 采集。

### 1.2 上游测试执行结果（11/11 PASS）

| # | 上游用例（README EXAMPLES / 正文） | 执行命令（`-n` 免硬件化） | 结果 |
|---|-----------------------------------|--------------------------|------|
| 1 | `dcled -t` | `dcled -n -e -t`（无限模式，20s 窗口收口） | ✅ PASS |
| 2 | `dcled -m 'Hello World!'` | `dcled -n -e -m 'Hello World!'` | ✅ PASS |
| 3 | `echo 'Hello World!' \| dcled` | `echo 'Hello World!' \| dcled -n -e` | ✅ PASS |
| 4 | `dcled f1 f2`（文件参数） | `dcled -n -e f1 f2` | ✅ PASS |
| 5 | `dcled --clock --repeat` | `dcled -n --clock --repeat`（无限模式，20s 窗口收口） | ✅ PASS |
| 6 | `dcled -p static -m 'Hello World'` | `dcled -n -e -p static -m 'Hello World'` | ✅ PASS |
| 7 | `dcled -p 2 -m 'Hello World'` | `dcled -n -e -p 2 -m 'Hello World'` | ✅ PASS |
| 8 | `dcled --test` | `dcled -n -e --test`（无限模式，20s 窗口收口） | ✅ PASS |
| 9 | `syslog \| dcled -e -p static` | syslog 行 \| `dcled -n -e -e -p static` | ✅ PASS |
| 10 | `dcled -h`（用法横幅，README 正文） | `dcled -h` | ✅ PASS |
| 11 | `cpuload`（构建产物，供仪表模式用） | `cpuload 0.2`（无限模式，20s 窗口收口） | ✅ PASS |

CI 采集到的机器可读结果：

```
HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "upstream-readme-examples",
  "discovered": 11, "executed": 11, "passed": 11, "failed": 0, "skipped": 0}
```

**说明**：`-t`、`--test`、`--clock --repeat`、`cpuload` 按上游设计是无限循环
（持续刷新显示/采样），测试以 20s 超时窗口收口，断言的是
"打印了预期内容且进程未提前崩溃"（区分退出码 `124`=正常被超时截断 与
`139`=SIGSEGV 崩溃，后者即补丁 1 所修复的缺陷）。

### 1.3 上游测试用例修改说明

- **未删除任何上游用例**：README EXAMPLES 段 9 条全部保留并执行。
- **未修改上游用例语义**：每条命令的参数与上游文档一致。
- 唯一的适配性改动是**为免硬件执行补上 `-n`（nodev）开关**：CI 环境无 Dream Cheeky
  消息板，而不带 `-n` 时程序会真的去 open 设备并失败退出。`-n` 是上游自带选项
  （`getopt` 选项串 `ho:m:b:s:T:p:g:G:dtrfencCB` 中的 `n`），属上游设计的正常用法，
  不改变被测代码路径 —— 事实上 `-n` 正是补丁 1 修复的崩溃路径，验证价值更高。
- **无限模式加超时窗口**：`-t` / `--test` / `--clock --repeat` / `cpuload` 上游设计为
  持续运行，不加窗口会挂死 CI。这是测试**执行方式**的约束，不是用例内容修改。

## 二、补全的消费者测试（适配侧新增）

### 2.1 测试文件

`test_package/test_dcled.py`（Python，subprocess 直启产物），
由 `test_package/conanfile.py` 的 `test()` 调用。

设计要点：

- **真实调用被测产物**：全部断言基于已安装的 `bin/dcled`、`bin/cpuload` 的实际
  stdout 与退出码，无空壳打印（满足 R34 / CI L1e 反向破坏性验证）。
- **subprocess 直启**：平台 conan runner 启动目标二进制恒 SIGSEGV，
  故自建 `subprocess.run` 并显式拼装 `LD_LIBRARY_PATH`（旁证：dry-run 中不设该变量、
  仅凭 `-Wl,-rpath` 也全部通过）。
- **可写目录探测**：平台 `/tmp` 只读（E002），按 `TMPDIR` → 当前目录 → `$HOME` 顺序探测。

### 2.2 断言清单（15 项，实测 15/15 PASS）

| # | 断言 | 类别 |
|---|------|------|
| 1 | `bin/dcled` 存在且可执行 | 产物完整性 |
| 2 | `bin/cpuload` 存在且可执行（同一 `all` 目标产出） | 产物完整性 |
| 3 | `dcled -h` 打印用法横幅（含 `Usage`） | 接口 |
| 4 | `dcled -n -e -m 'OHOS dcled'` 回显消息 —— **SIGSEGV 回归守卫** | 功能 + 回归 |
| 5 | `dcled -n -e` 从 stdin 读消息（管道） | 功能 |
| 6 | `dcled -n -e f1 f2` 回显文件内容 | 功能 |
| 7 | 文件参数按给定顺序处理（f1 先于 f2） | 功能 |
| 8 | `-p static` 前言按名称选择 | 功能 |
| 9 | `-p 2` 前言按编号选择 | 功能 |
| 10 | 字体数据打包（`share/dcled` 下 ≥2 个 `.dlf`） | 数据完整性 |
| 11 | `FONTDIR` 指向包内路径（`-t` 打印的 font directory） | 包装正确性 |
| 12 | `cpuload 0.2` 持续输出采样 | 功能 |
| 13 | `cpuload` 周期性采样为 0-100 数值（首个采样为开机累计值差分，上游 `int` 截断可越界，不对其断言） | 功能 |
| 14 | dcled/cpuload 退出码语义（`-n` 路径非 139） | 回归 |
| 15 | 消费者测试整体 15/15 | 汇总 |

实测输出（`conan create` 日志内）：

```
CONSUMER TEST RESULT: 15/15 assertions passed
```

### 2.3 补全用例与上游用例的关系（不重复计数）

- 上游 11 项：验证 `dcled`/`cpuload` 的**命令行行为符合上游文档**
  （README EXAMPLES 逐条）。
- 适配侧 15 项：验证**已安装包作为 Conan 制品的正确性** —— 产物可执行位、
  字体数据随包交付、`FONTDIR` 烘焙为包内路径、rpath 可独立解析依赖
  （第 4、6、7、10、11 项是上游用例未覆盖的**包装层**语义）。
- 两者的判定对象不同（源码行为 vs 制品契约），不存在同一消费者测试步骤
  被拆成多个用例的虚增；上游 11 项在 `build()` 阶段执行、15 项在 `test()`
  阶段执行，计数口径相互独立。

## 三、门禁与静态检查

| 门禁 | 内容 | 结果 |
|------|------|------|
| G1 | 配方完整性（conanfile.py / conandata.yml / test_package/） | ✅ PASS |
| G2 | `conan create` 干净构建（配方自包含性） | ✅ PASS |
| G3 | 系统同名库隔离（R26：对比 `/lib`、`/lib64` 基名） | ✅ PASS（libusb-1.0.so **非**系统同名库，保留动态链接） |
| G4 | 产物完整性（bin / lib / include） | ✅ PASS（`bin/dcled` 195008 B、`bin/cpuload` 27072 B、`share/dcled/`） |
| L2 | 最小冒烟测试 | ✅ PASS |
| L4 | 静态安全扫描（NX / PIE / RELRO） | ✅ PASS |
| L5 | 产物基线（SHA256） | ✅ PASS |

## 四、手工验证记录（补丁有效性证据）

| 验证项 | 补丁前 | 补丁后 |
|--------|--------|--------|
| `dcled -n -e -m 'Hello World!'` | exit **139** (SIGSEGV) | exit **0**，输出 `Hello World!` |
| `dcled -h` | exit 0 | exit 0（1404 B 用法横幅） |
| `echo 'Hello World!' \| dcled -n -e` | exit 139 | exit 0，输出 `Hello World!` |
| `dcled -n -e -p static -m 'Hello World'` | exit 139 | exit 0，输出 `Hello World` |
| `cpuload 0.2` | exit 124（无限采样被超时截断，未受影响） | exit 124（无限采样被超时截断），持续输出负载数值 |

补丁 `patches/0001-init-ledscreen-maindisp.patch` 应用性验证：
`git apply --check` rc=0，实际应用 rc=0，二进制随后通过全部 26 项检查。

## 五、环境与已知限制

- **无硬件依赖**：全部自动化测试以 `-n`（nodev）模式运行，帧内容输出到 stdout
  而不发送到设备。真实消息板显示未在 CI 中验证（环境无该 USB 设备）。
- `gcc` 在构建机不存在，全部编译经 `CC=clang`（取自 Conan
  `tools.build:compiler_executables`，R33）。
- 22 处 K&R 风格函数定义在 clang 下产生弃用警告，不影响功能与门禁。
- 平台 `/tmp` 只读（E002），测试临时文件落在 `TMPDIR`/工作目录。
