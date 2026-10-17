# j4-dmenu 3.2 — 测试报告

**软件**: j4-dmenu（j4-dmenu-desktop）3.2
**适配目标**: OpenHarmony PC / HarmonyOS PC（`aarch64-unknown-linux-ohos`）
**报告日期**: 2026-09-25（首版） / 2026-09-26（新增消费者端到端 + 鸿蒙平台特有测试）
**状态**: built

## 1. 环境（真实设备实测）

| 项 | 值 |
|---|---|
| 宿主 | HarmonyOS PC aarch64（OHOS 产物可在本机直接执行，测试为真实运行结果） |
| 编译器 | clang / clang++ 15.0.4（OHOS SDK 26.0.0.18） |
| C++ 标准库 | libc++ |
| 构建系统 | CMake（`conan create` 驱动） |
| Conan | 2.29.1 |
| profile | `ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8, clang 15） |
| 依赖 | spdlog 1.17.0 / fmt 12.2.0 / catch2 3.16.0（制品仓已发布版本，静态链接） |

复现命令：

```bash
conan create archives/j/j4-dmenu/3.2 \
  -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 \
  -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 -b missing
```

## 2. 上游测试（Catch2 单元测试，经 CTest）

- 注册命令：上游 `catch_discover_tests` 在构建期生成 CTest 用例
- 执行命令：`ctest --test-dir <build_folder> --output-on-failure -j8 --timeout 60 -E pytest`

### 结果

```text
100% tests passed, 0 tests failed out of 79

Total Test time (real) =   1.00 sec
```

| 指标 | 数值 | 占比 |
|---|---|---|
| 总测试数 | 79 | 100% |
| 通过 (PASS) | 73 | 92.4% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 6 | 7.6% |

> 上表为可机读汇总（供 `submission.py _extract_test_summary` 取数）；
> 其中「总测试数」= CTest 注册用例数，「通过」= 真实执行并通过数。

> **口径说明（按实记录）**：`100% tests passed, 0 tests failed out of 79` 是 CTest 对
> **未失败**用例的比例表述；其中 6 个用例在 CTest 中标记为 `***Skipped`，
> 因此**真正执行并通过的是 73 个**，不是 79 个。本报告不采用"79/79 全通过"的说法。

### 6 个跳过用例及其原因

| CTest# | 用例名 | 跳过原因 |
|---|---|---|
| 11 | Test I3Exec | `mkdtemp: Read-only file system` |
| 24 | Test conversion from v0 to v1 | 同上（依赖 `/tmp` 下临时文件） |
| 42 | Test imperfect conversion from history v0 to v1 | 同上 |
| 48 | Test loading history | 同上 |
| 55 | Test overwriting with add() | 同上 |
| 58 | Test reading a unreadable file. | 同上 |

**根因（环境限制，非上游缺陷、非适配引入）**：上游测试把临时目录**硬编码**为
`/tmp/`（见 `tests/FSUtils.cc:157` 与 `tests/TestI3Exec.cc:106`），
且仅在 `mkdtemp()` 失败时以 `SKIP()` 优雅退出（上游设计如此）。
本机 `/tmp` 是只读 `erofs` 挂载（`/dev/block/dm-0 on /tmp type erofs (ro,...)`，
属 root 所有），`mkdtemp` 必然失败，故这 6 个用例被上游自身的守卫跳过。

实测证据（直接执行测试二进制，取上游给出的跳过消息）：

```text
tests/TestI3Exec.cc:108: SKIPPED:
explicitly with message:
  mkdtemp: Read-only file system
test cases: 1 | 1 skipped
```

已尝试但仍无法让这 6 个用例落地执行：设置 `TMPDIR` 无效（上游路径硬编码，不读 `TMPDIR`）；
本机亦无 `proot` / `bwrap` / `unshare` / `fakeroot` / `fakechroot` / 容器运行时可用，
无法为测试提供一个可写的 `/tmp` 视图。**这 6 个用例的跳过属环境的确定性限制，
在具备可写 `/tmp` 的环境（如常规 CI runner）中可正常执行。**

### 上游 pytest 系统测试（12 项）：本环境未注册

上游 `CMakeLists.txt:138-142` 在 configure 期探测 `pytest --version`，
探测失败即 `message(WARNING "pytest executable is not available. Skipping pytest tests...")`
并**跳过注册**。本构建环境未提供 `pytest`，故 CTest 中不存在 `pytest-system-tests` 条目——
这是**上游自身的既有降级行为**，非适配改动。

上游 `tests/system_tests/system_test.py` 含 12 个 `test_*`（配合
`helper_scripts/dmenu_*_imitator.sh` 伪 dmenu 脚本，属消费者/系统级测试）。
该层级的覆盖由本次新增的 `test_e2e.sh` 以**不依赖 pytest** 的方式补足（见 §3.2）。

## 3. test_package（消费者视角测试，三层）

`test_package/conanfile.py` 的 `test()` 依次调用三个脚本，全部针对
**安装后的产物** `<pkg>/bin/j4-dmenu-desktop` 执行：

| 脚本 | 层级 | 断言/用例数 | 结果 |
|---|---|---:|---|
| `test.sh` | 冒烟 | 3 断言 + 2 前置检查 | PASS |
| `test_e2e.sh` | **完整消费者端到端** | 9 用例 / 14 断言 | PASS |
| `test_ohos.sh` | **鸿蒙平台特有** | 16 断言 | PASS |

> OHOS 约束：`/system/bin/sh`（mksh）不能可靠地直接 exec ELF，
> 故三个脚本一律由 `conanfile.py` 用 bash 包裹执行（`CONFIG_SHELL` → PATH → 固定路径三级解析）。

### 3.1 冒烟测试 `test.sh`

```text
[test] j4-dmenu-desktop --version
3.2
✅ --version reports 3.2
[test] j4-dmenu-desktop --help
✅ --help exit 0
✅ --help documents --dmenu
✅ test_package j4-dmenu/3.2 passed
```

| 指标 | 数值 |
|---|---|
| 检查项 | 5 |
| 通过 | 5 |
| 失败 | 0 |

检查明细（3 项输出/退出码断言 + 2 项产物前置检查）：

1. `j4-dmenu-desktop --version` 输出为 `3.2`（断言）；
2. `j4-dmenu-desktop --help` 退出码为 0（断言）；
3. `--help` 输出中包含 `--dmenu`（断言，证明这是完整构建的主程序而非残缺产物）；
4. 安装产物 `bin/j4-dmenu-desktop` 存在且具备可执行权限（前置检查）；
5. 该二进制在 OHOS 宿主上可被正常加载执行、无动态库缺失（前置检查）。

> 说明：第 4/5 项是"产物存在且可执行"的前置检查，不是独立的行为断言；
> 真正验证行为的是第 1–3 项。此处按 5 项检查如实计数，不夸大为 5 条断言。

### 3.2 完整消费者端到端测试 `test_e2e.sh`（9 用例 / 14 断言）

**方法**：构造**隔离的 XDG 桌面环境**（`XDG_DATA_HOME` 指向临时沙箱的
`applications/`，`XDG_DATA_DIRS` 指向空目录）+ **伪 dmenu**
（复刻真实 dmenu 的 stdin/stdout 协议：读候选列表、回显 `$J4D_PICK`），
驱动被测二进制走完 **扫描 `.desktop` → 解析 → 过滤 → 生成候选列表 → 呈现给 dmenu
→ 收回用户选择 → 组装命令行 → `fork/execvp` 启动目标程序** 全链路。

**判定标准**：以「目标程序是否**真的被启动**、**收到了什么参数**」为断言依据
（目标程序把 `argc`/`args` 写入文件回读），而非仅看退出码。

实测输出：

```text
[case C0] 无头(headless)运行：不依赖 DISPLAY，--version/--help 正常
  ✅ 无 DISPLAY 时 --version 正常工作（输出 3.2）
  ✅ 无 DISPLAY 时 --help 退出码 0
[case C1] 基础全链路：候选列表内容 + 选中项被真实启动 + 只启动选中项
  ✅ 候选列表正确（3 项，含中文条目）
  ✅ 选中程序被真实 execvp 启动，Exec 参数原样传递
  ✅ 仅启动选中项，未误启动其他条目
[case C2] NoDisplay=true 的条目不进候选列表
  ✅ NoDisplay 条目被正确过滤（候选列表无 J4D E2E Hidden）
[case C3] -x 按 XDG_CURRENT_DESKTOP 过滤 OnlyShowIn=kde 条目
  ✅ kde 会话：OnlyShowIn=kde 条目出现在候选列表
  ✅ GNOME 会话：OnlyShowIn=kde 条目被正确过滤
[case C4] 用户输入任意命令（不在候选列表）→ 真实启动且参数原样传递
  ✅ 自定义命令被真实启动，参数 hello world 原样到达目标程序
[case C5] 中文条目：候选列表与真实启动双断言
  ✅ 中文条目端到端跑通（候选列表 UTF-8 保真 + 真实启动）
[case C6] --usage-log 首次记录 + 二次运行历史项排序优先
  ✅ 使用历史真实落盘并记录所选项
  ✅ 二次运行历史项排序优先（首位 = 上次所选项）
[case C7] --wrapper：包装命令后仍能真实启动目标程序
  ✅ wrapper 链路跑通（wrapper 收到完整目标命令行）
[case C8] --no-exec 仅输出组装后的命令，不启动任何进程
  ✅ --no-exec 输出组装命令且未启动进程
[e2e] 完整消费者用例：9 个用例 / 14 条断言全部通过
✅ test_package 端到端消费者测试 j4-dmenu/3.2 通过
```

| 指标 | 数值 |
|---|---|
| 用例数 | 9 |
| 断言数 | 14 |
| 通过 | 14 |
| 失败 | 0 |

**覆盖的端到端行为**：

| 用例 | 验证的鸿蒙消费者场景 |
|---|---|
| C0 | 无头约束：无 `DISPLAY` 时核心入口可用 |
| C1 | 基础全链路：候选列表生成 → 选择 → 真实 `execvp`；且只启动选中项 |
| C2 | `NoDisplay=true` 条目过滤（`src/Application.cc:138`） |
| C3 | `-x` + `XDG_CURRENT_DESKTOP` 大小写敏感的 `OnlyShowIn` 过滤 |
| C4 | 用户输入不在候选列表的任意命令 → 直通执行、参数原样 |
| C5 | 非 ASCII（中文）条目的候选列表保真与真实启动 |
| C6 | `--usage-log` 使用历史落盘 + 二次运行排序优先 |
| C7 | `--wrapper` 包装链路 |
| C8 | `--no-exec` 干跑不启动进程 |

> 说明：C3 的 `OnlyShowIn` 匹配**大小写敏感**（XDG 规范），故 kde 会话下用规范小写
> `kde` 触发正例、`GNOME` 触发反例。该行为在编写断言前已对真实 OHOS 二进制实测确认。

### 3.3 鸿蒙平台特有测试 `test_ohos.sh`（16 断言）

**方法**：直接检查安装后产物的**平台形态**，并验证**鸿蒙平台约束下的运行行为**
（这些约束在常规 Linux/glibc 桌面发行版上不存在）。

实测输出：

```text
[ohos] binary : <pkg>/bin/j4-dmenu-desktop
[ohos] readelf: /data/service/hnp/bin/readelf (GNU readelf (GNU Binutils) 2.45)
  ✅ #1 ELF class = ELF64
  ✅ #2 Machine = AArch64
  ✅ #3 Type = DYN（Position-Independent Executable）
  ✅ #4 .interp = /lib/ld-musl-aarch64.so.1（musl，非 glibc）
  ✅ #5 readelf -l 的 program interpreter 与 .interp 一致
  ✅ #6 RUNPATH 仅基于 $ORIGIN（可重定位）：[$ORIGIN/../lib:$ORIGIN/../lib/external]
  ✅ #7 动态依赖仅 musl 体系（无 glibc 专有库）：[libc++_shared.so] [libc.so]
  ✅ #8 .note.ohos.ident 存在且含 OHOS 标识
  ✅ #9 .codesign 节存在（鸿蒙专有，Linux 二进制无）
  ✅ #10 无 TEXTREL，加载期重定位合规
  ✅ #11 /system/bin/sh (mksh) 与 bash 均可执行产物（均报告 3.2）
  ✅ #12 只读 /tmp（read-only）下 Terminal=true 优雅报错 rc=1、无崩溃
  ✅ #13 鸿蒙 PC 无 dmenu 时优雅结束（rc=0，无崩溃/无信号终止）
  ✅ #14 无头(headless)约束：无 DISPLAY 时 --version 正常（不依赖 X 会话）
  ✅ #15 从安装前缀直接可运行（无需 LD_LIBRARY_PATH，无动态库缺失）
  ✅ #16 产物完备：bin/ + man 手册 + bash/zsh/fish 三种补全
[ohos] 鸿蒙平台特有断言：16/16 全部通过
✅ test_package 鸿蒙平台特有测试 j4-dmenu/3.2 通过
```

| 指标 | 数值 |
|---|---|
| 断言数 | 16 |
| 通过 | 16 |
| 失败 | 0 |

**逐项说明（为什么是"鸿蒙特有"）**：

| # | 断言 | 鸿蒙相关性 |
|---|---|---|
| 1–3 | ELF64 / AArch64 / PIE(DYN) | 鸿蒙 PC 目标三元组 `aarch64-unknown-linux-ohos` 的产物形态要求 |
| 4–5 | `.interp` = `/lib/ld-musl-aarch64.so.1` | 鸿蒙用 **musl** 而非 glibc 的 `ld-linux` |
| 6 | RUNPATH 仅 `$ORIGIN` 相对路径 | 制品包**可重定位**，不含构建机绝对路径（避免打包环境泄漏） |
| 7 | 动态依赖无 `libstdc++`/`libgcc_s`/`ld-linux` | 印证 musl + libc++ 工具链，无 glibc 专有库混入 |
| 8–9 | `.note.ohos.ident`、`.codesign` | **OHOS 专有 ELF 节**，Linux 二进制不存在；鸿蒙签名/身份标识 |
| 10 | 无 `TEXTREL` | 加载期只读重定位（OHOS 加载器约束） |
| 11 | mksh（`/system/bin/sh`）与 bash 双 shell 可执行 | 鸿蒙默认 shell 为 mksh，与 Linux 桌面默认 bash 不同 |
| 12 | 只读 `/tmp` 下 `Terminal=true` 优雅报错 | 本机 `/tmp` 为只读 `erofs`；验证"环境受限时不崩溃" |
| 13 | 无 dmenu 时优雅结束 | **鸿蒙 PC 无 dmenu**（桌面环境能力缺口），验证降级行为 |
| 14 | 无 `DISPLAY` 可运行 | 鸿蒙 PC 无 X 会话（无头约束） |
| 15 | 免 `LD_LIBRARY_PATH` 可直接运行 | 验证包内 `lib/` 与 `$ORIGIN` RUNPATH 生效、无库缺失 |
| 16 | 产物完备（bin + man + 3 种补全） | 验证 `conan create` 安装产物完整，非残缺包 |

> 说明：#12/#13 采用"**环境相关分支**"判定——只读 `/tmp` 时要求 **rc=1 且给出错误说明**，
> 可写时要求 **rc=0**；两种情况下都额外断言"**无崩溃、无信号终止**"。
> 本机实测为只读 `erofs` 分支。

### 3.4 三层如何接入流水线

`test_package/conanfile.py` 的 `test()` 依次 `self.run()` 上述三个脚本，
故 **`conan create` 即自动完成三层消费者测试**；任一断言失败即 `conan create` 失败，
不存在"脚本写了但没人跑"的情况。

## 4. CI 门禁结果（`ci/conan/build_and_test.sh`）

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: j4-dmenu-desktop --version OK
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
Pass rate: 100.0% (1/1)
```

- `L1e`（R34 破坏性负向测试）：pass — 移走 `bin/` 后冒烟检查如期失败，证明测试确实依赖真实产物；
- 全流程 `Total: 1 / Success: 1 / Failed: 0`。

## 5. 断言计数口径

上游 17 个 Catch2 测试源，静态计数为 **258 处 REQUIRE 族断言宏**
（`REQUIRE` 228 + `REQUIRE_FALSE` 16 + `REQUIRE_NOTHROW` 8 + `REQUIRE_THROWS` 6），
**另有 2 处 `CHECK`**（`CHECK` 2 + `CHECK_FALSE` 0），合计 **260 处断言宏**；
另有 **21 处 `SECTION`**。这是**源码中断言宏的出现次数**，非运行期执行次数
（`SECTION` 会重复执行其父级断言，故运行期断言次数高于该值）。
先前记录中的"267 处断言"无实测出处，已在此更正为可复现的 258（REQUIRE 族）/ 260（含 CHECK）。

本次 test_package 侧的断言计数为实测（脚本内 `ok()` 计数输出），非静态估算：
`test.sh` 3 断言 + `test_e2e.sh` 14 断言 + `test_ohos.sh` 16 断言 = **33 条断言**。

## 6. 源码补丁情况

**零源码补丁**。`patches_applied: []`，全部适配通过 `conanfile.py` 的
`generate()`（工具链变量 + 依赖 `cpp_info` 覆盖）完成，上游文件一字未改。
详见 `notes.md` 与知识草稿 `knowledge/drafts/E620-draft-693C.md`、
`knowledge/drafts/E639-draft-2264.md`。

## 7. 结论

- 上游单元测试 **73 个真实执行、全部通过，0 失败**（OHOS 宿主直接运行）；
  6 个因本机 `/tmp` 只读被上游 `SKIP()` 守卫跳过，原因已逐条记录；
- 上游 12 项 pytest 系统测试因本环境无 `pytest` 而未注册（上游 CMake 既有降级行为），
  该层级覆盖由新增的 `test_e2e.sh` 以不依赖 pytest 的方式补足；
- `test_package` 三层测试全部通过：
  - 冒烟 `test.sh` **5/5 检查通过**，`--version` 报 3.2；
  - **完整消费者端到端 `test_e2e.sh` 9 用例 / 14 断言全通过**（真实 `execvp` 启动目标程序）；
  - **鸿蒙平台特有 `test_ohos.sh` 16/16 断言全通过**；
- W3 本地 CI 全绿（L0/L1/L2/L5 pass，L4 patches clean，L1e 负向测试通过）；
- 版本 `manifest.yaml` 状态为 `built`，未升为 `published`
  （`published` 需在可写 `/tmp` 环境补齐上述 6 个上游用例或经人工确认，故不擅自升级）。
