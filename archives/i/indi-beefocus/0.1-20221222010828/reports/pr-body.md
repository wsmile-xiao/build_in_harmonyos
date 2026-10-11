## PR 信息

- **三方库名称**：indi-beefocus
- **上游版本**：0.1+20221222010828（上游快照 v0.1，日期戳 2022-12-22 01:08:28；包版本 `0.1-20221222010828`，与上游源码版本一致，仅将 `+` 规范化为 `-`）
- **上游仓库地址**：https://github.com/indilib/indi-3rdparty
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 8 | 来源：`unit_tests/test_driver.cpp`（gtest，8 个 `TEST(DEVICE, …)`），由 `CMakeLists.txt` 的 `add_test(run-tests test_driver)` 注册为 1 个 CTest 条目；驱动走软件模拟固件，无需真实硬件 |
| 集成测试 | 0 | 上游无集成测试套件 |
| 其他测试 | 0 | 上游无其他测试 |
| **合计** | **8** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 8 | 不变 | 上游 8 个 gtest 用例原样保留，在 OHOS 环境实跑全部通过 |
| 集成测试 | 0 | 不变 | 上游无集成测试 |
| 鸿蒙特有测试 | 4 | 新增 | test_package 4 个具名消费者端到端用例（HC-1..HC-4），内部共 31 项检查；HC-4 为鸿蒙平台特有 |
| **合计** | **12** | **+4** | |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 说明：上游 `unit_tests/` 下 3 个文件（`test_driver.cpp` / `test_helpers.h` / `test_helpers.cpp`）与 8 个用例**零修改**。适配所用的 4 个补丁全部作用于构建系统与驱动源码（`FindINDI.cmake` / `CMakeCommon.cmake` / `driver/beefocus.cpp` / `CMakeLists.txt`），未触碰任何测试用例。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 更正说明：本库**上游有测试**（8 个 gtest 用例，见上表），但**没有针对"交付产物被下游消费"这一层的测试**——上游单元测试是进程内直接编译驱动源码，不消费打包产物。因此适配后补全的是**消费者视角**的用例，而非补上游缺失的单元测试。

> 若选择「是」，须说明：
> - **补全的测试范围**：为交付产物新增 4 个具名消费者端到端用例（HC-1..HC-4），共 31 项检查，覆盖 CLI 契约、INDI 协议消费、INDI 描述文件、鸿蒙打包不变量
> - **补全原因**：本配方产物是**驱动可执行文件**（`bin/indi_beefocus`）而非库，上游现有测试不执行打包后的二进制、不校验包内制品，无法验证"交付物可被真实消费"（R34 要求 test_package 实质依赖被测包）
> - **新增测试文件清单**：
>   1. `test_package/conanfile.py` — 消费者测试配方，`test()` 中经 `self.run()` 真实执行包内驱动二进制（`can_run()` 为假时直接失败，不允许跳过）
>   2. `test_package/test_indi_beefocus.py` — 4 个具名用例（HC-1..HC-4）的实现，全部断言落在包内真实制品上
>   3. `test_package/MANIFEST.yml` — 上游测试声明（含 R51 清点结果与用例清单）

---

## 验证结果

- 编译状态：**通过**
- 上游测试用例通过率：**8/8（100%）**
- 新增测试用例通过率：**4/4（100%）（31/31 检查项 0 失败）**

---

## 补充说明

### 1. 产物形态

本包产物是 INDI **驱动可执行文件**，不是库：

| 路径 | 说明 |
|---|---|
| `bin/indi_beefocus` | INDI 驱动可执行文件（aarch64/OHOS） |
| `share/indi/indi_beefocus.xml` | INDI 驱动描述（供 indiserver / 客户端发现） |
| `licenses/LICENSE` | 上游 LGPL-2.1+ 许可证原文 |

因此软件级提供 `commands.json`（R38/L0k），`package_type = "application"`。

### 2. 依赖

- `libindi/2.2.2.1`（已发布到 ohpcd 制品仓，`conan download` 实测 rc=0）
- `gtest/1.17.0`（`test_requires`，仅上游单元测试使用，不进交付依赖）

无待适配的底层依赖，不涉及依赖库附加分。

### 3. 源码来源（R39/PF7）

上游 `indilib/indi-3rdparty` **不为单个 3rdparty 驱动打 tag**，且该子项目在 v2.2.x 系列中已不再随 monorepo tarball 发布。本仓库既有先例（libplayerone 3.1.0）对同类情况采用 Debian Astronomy Team 在 salsa 上维护的官方上游 tag 快照，本配方沿用同一来源：

```
https://salsa.debian.org/debian-astro-team/indi-beefocus/-/archive/upstream/0.1+20221222010828/indi-beefocus-upstream-0.1+20221222010828.tar.gz
```

**来源可信性已实证**：该快照与 Debian 归档的 `orig.tar.gz` **逐文件、逐字节完全一致**（95 个文件全量 sha256 比对，文件清单与内容哈希 diff 均无输出，见 `notes.md`「源码来源核验」）。未使用任何镜像前缀、明文 http、个人 fork 或 Debian pool 重打包源。

### 4. 补丁（4 个，均不含平台宏）

| 补丁 | 内容 | 性质 |
|---|---|---|
| `0001-FindINDI.cmake.patch` | 版本正则回移上游 master，兼容 INDI 2.x `#define INDI_VERSION "2.2.2"` 的引号形式（否则 `FATAL_ERROR failed to detect INDI version`） | 上游同步（非平台相关） |
| `0002-CMakeCommon-cxx17.patch` | 供应商 `CMakeCommon.cmake` 将 `CMAKE_CXX_STANDARD` 固定为 14；INDI 2.x 头文件（`std::any`）与 gtest 1.17 都要求 C++17 → 提升到 17（与上游 master 一致） | 上游同步（非平台相关） |
| `0003-beefocus-indi2-api.patch` | 驱动源码 INDI 1.x → 2.x 属性 API 移植（`FocusAbsPosN/FocusMaxPosN` → `FocusAbsPosNP/FocusMaxPosNP` 访问器、`.s =` → `setState()/getState()`、`IDSetNumber()` → `apply()`），**逐行等同上游 master 现已携带的同一处移植** | 上游同步（非平台相关） |
| `0004-CMakeLists.txt.patch` | ①`cmake_minimum_required(VERSION 3.0)` 在 CMake ≥4 下硬报错 → 提升到 3.16（上游 master 同值）；②单元测试 POST_BUILD 用裸 `COMMAND ${TEST}` 导致 shell `Error 127` → 改 `$<TARGET_FILE:${TEST}>`；③`find_package(INDI)` 收窄为 `COMPONENTS driver`（本驱动不使用 alignment/client 子系统） | 上游缺陷修复 + 本平台需要 |

**R8 合规**：4 个补丁新增行**均不含 `__OHOS__` 等平台宏**，无平台条件编译分支，全部为"上游 master 已有 / 与平台无关的构建缺陷修复"，`patch_classification.platform_only = false`（逐条 rationale 见版本级 `manifest.yaml`）。

### 5. 平台适配要点

- **E092**：CMake 不识别 HarmonyOS → `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`（与 `libindi` / `libfli` 同款）。
- **`CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF`**：供应商 `cmake_modules/FindINDI.cmake` 用 legacy `find_library` 变量，需在 toolchain 末置覆盖 Conan 默认的 `ON`。
- **E537（本包关键决策）**：本平台无法对 Conan 缓存中的 OHOS 共享库做 `mmap PROT_EXEC` 加载（`libindidriver.so` / `libindiAlignmentDriver.so` 均 `Permission denied`；对照实验确认 `libusb`/`libfftw3` 及本机新编 `.so` 均正常加载，排除体积/权限位/TEXTREL 等因素）。因此驱动**静态链接 `libindidriver.a`**，并需 `-Wl,--allow-multiple-definition`（归档内 `indidrivermain.o` 自带 `main`/`me`）。这与本仓库 `libindi` 自身 test_package 的做法一致。
- **传递依赖注入**：供应商 `FindINDI.cmake` 无 CONFIG 感知，libindi 的传递依赖（cfitsio/nova/libusb/curl/gsl/fftw3/libev/jpeg/zlib）由配方从 Conan 依赖图**动态生成** `-L/-l`（不硬编码）。
- **构建树 RPATH**：构建期可执行文件（POST_BUILD + ctest）需显式 `-Wl,-rpath,<dep libdir>`，OHOS 加载器不会自动搜索 Conan 缓存目录。

### 6. 已知限制（诚实说明）

HC-2 最初写成"捕获 `<def>` 输出并断言设备名/属性名"，实测**不成立**并已修正为可观测断言。原因是上游行为（非本适配引入）：`libs/indibase/indidrivermain.c` 的 `clientMsgCB()` 把收到的 XML 交给 `deferMessage()` 排队，真正的 `dispatch()` 由事件循环迭代触发；而管道 EOF 时驱动直接 `exit(1)`，因此一次性管道喂入请求无法捕获 `<def>` 应答。真实使用场景由 `indiserver` 常驻拉起驱动（stdin 不关闭），不受影响。修正后的 HC-2 断言可观测事实：驱动确实经 INDI 协议路径消费请求（`-v` 回显）+ 交付 ELF 确实含 7 个驱动自有入口与 4 个 INDI 协议入口符号。此修正避免了"形式通过、实质空转"的假测试（R34）。详见 `notes.md`「HC-2 的诚实说明」。

### 7. 验证证据

- 上游 8/8 gtest 用例与 test_package 4 用例 / 31 检查的完整实测日志：`reports/r51-upstream-tests.log`
- 复现命令：
  ```sh
  cd archives/i/indi-beefocus/0.1-20221222010828
  conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable
  ```
  `rc=0`，日志含 `[  PASSED  ] 8 tests.` 与 `== 4 cases, 0 failed == / == 31 checks, 0 failures == / RESULT: PASSED`

### 8. TODO / 后续

- 无待办阻断项。
- 上游 indi-3rdparty master 的 `beefocus` 已带 INDI 2.x 移植；补丁 0002/0003 与其等价，待上游为子项目打 tag 后可直接切换官方源并弃用补丁。
- 潜在路径 B 素材（本轮不提交，先保路径 A）：本包与 `libfli` / `libindi` 共同构成「indi-3rdparty 系子项目适配模式」（E092 + FindINDI 收窄 + E537 静态链接 + 传递依赖注入四件套），具备提炼为通用新 SKILL 的形态。

---

## 模板使用说明

| 填写项 | 是否必填 | 说明 |
|--------|---------|------|
| 三方库名称及上游版本 | 必填 | 用于追溯上游变更 |
| 测试用例对比表格 | 必填 | 用于追溯上游测试用例完整性 |
| 上游测试修改说明 | 条件必填 | 若存在修改则必填，须逐条说明原因与内容 |
| 测试补全说明 | 条件必填 | 若上游无测试且适配后补全则必填 |
| 验证结果 | 必填 | 由参赛者填写本地验证结果 |

## 常见场景示例

**场景一：上游有完整测试，适配后保持不变**
上游 120 个单元测试 + 30 个集成测试，适配后全部通过，测试用例无修改。
测试用例对比：合计 150 → 150（不变），未修改上游测试，无需补全。

**场景二：上游有测试，部分需修改以适配鸿蒙**
上游 80 个单元测试，其中 3 个与 POSIX 文件路径相关，因鸿蒙文件系统差异需修改断言。修改后全部通过。
测试用例对比：合计 80 → 80（不变），修改上游测试 3 处（路径断言），无需补全。

**场景三：上游无测试，适配后补充**
上游库仅提供示例代码，无正式测试框架。适配后补全 45 个单元测试、8 个集成测试，全部通过。
测试用例对比：合计 0 → 53（+53），未修改上游测试（上游无测试），已补全。

**场景四：上游有测试 + 适配后针对鸿蒙新增测试**
上游 60 个单元测试全部保留并通过。另新增 15 个鸿蒙特有场景测试（如窗口管理、输入法适配）。
测试用例对比：合计 60 → 75（+15 新增），未修改上游测试，无需补全（上游已有测试）。

> **本包归属场景四**：上游 8 个单元测试全部保留并通过（8 → 8 不变），另新增 4 个鸿蒙平台消费者用例（合计 8 → 12，+4），未修改上游测试。

---

### 关于建 PR 前硬闸 PF9（框架已知冲突，已用官方逃生口）

`create-pr` 的 **PF9「分支/路径闸」**要求所有 `archives/` 变更路径至少 5 段
（即落在 `archives/<字母>/<包>/<版本>/…` 内）。但 **R38** 与 **PF8** 都要求 CLI
工具的 `commands.json` 放在**软件级** `archives/<字母>/<包>/commands.json`，只有
4 段——两条规则对每一个 CLI 包都直接冲突。

本包被 PF9 命中的正是 R38 强制要求的软件级文件：

```
archives/i/indi-beefocus/README.md
archives/i/indi-beefocus/commands.json      ← R38 强制，不能删除 / 不能移入版本目录
archives/i/indi-beefocus/manifest.yaml
```

`commands.json` **不能**为了绕过 PF9 而删除或移入版本目录：PF8 在软件级读取它，
移走会导致 CI L0k 反过来判 `CLI tool detected but commands.json missing`，把 CI 弄红。
本包 `package_type = "application"`、`cpp_info.bindirs = ["bin"]`，是确定的 CLI 包。

因此按 skill §3 记载的官方逃生口使用 `--no-preflight` 建 PR。已逐闸确认**除 PF9
外的全部前置硬闸均通过**：

| 闸 | 结果 |
|---|---|
| PF1 单包闸 | pass（仅 `archives/i/indi-beefocus`） |
| PF2 制品闸 | pass（无压缩包/归档） |
| PF3 测试闸 | pass（test() 有真实 self.run，测试源完整，MANIFEST 齐全） |
| PF4 依赖闸 | pass（`libindi/2.2.2.1` 已在制品仓） |
| PF5 平台宏闸 | pass（4 个补丁新增行 `__OHOS__` 命中数 = 0） |
| PF6 前缀闸 | pass（无 SYS_PREFIX / 共享 `/usr/local` 注入） |
| PF7 源 URL 闸 | pass（salsa 官方上游 tag 快照，非镜像/非重打包 pool） |
| PF8 配方静态闸 | pass（settings 四项齐全、slug/version 一致、CLI 包有 commands.json） |
| **PF9 分支/路径闸** | **仅因 R38 强制的软件级 `commands.json` 等 3 个文件报错；分支名 `feat/indi-beefocus-0.1-20221222010828` 本身符合 PF9 期望** |
| R52 审计交叉校验 | pass（审计 pass 且无 P0/P1 硬闸命中，不构成审计失真） |

已确认 CI 侧 G0 / JC / KC / L0（含 L0j 版本占用、L0k commands.json、L0m 目录结构、
L0n 分支名、L0p settings）/ L2 / L4 / L5 的定位逻辑与本包一致，不会因此报错。

> 同类先例：`swapspace` 1.18（PR 同日合并，commit `758c729f21`）遇到完全相同的
> PF9/R38 冲突，采用同一逃生口，并在其 PR 描述中做了相同说明。

### 关于 PF9 拦截的一个前置问题（已在本 PR 内修复）

首次调用 `create-pr` 时 preflight 报出数十条**与本包无关**的 PF7 命中
（qzxing / rbootd / swapspace / trickle 等他人包）。根因是**本地 `main` 分支过期**：
本地 `main` 落后 `origin/main` 407 个提交，preflight 以 `main...HEAD` 计算变更，
把他人已合并的存量一并算入（3033 个文件）。已将本地 `main` **纯快进而非重置**同步到
`origin/main`（`main` 是 `origin/main` 的祖先，零提交丢失），同步后 `main...HEAD`
恢复为 **16 个文件，全部属于本包**。
