# far2l 2.8.0 适配笔记

## 编译环境
- 构建系统: CMake（纯 CMake，无 autotools）
- 编译日期: 2026-08-16
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 目标平台: HarmonyOS (aarch64, musl libc)
- 状态: built

## 构建配置

far2l 上游提供丰富的编译开关，本适配根据设备环境做如下收敛：

| 开关 | 值 | 理由 |
|------|------|------|
| USEWX | NO | wxWidgets GUI 后端未适配，OHOS 无可运行桌面 |
| TTYX | NO | X11 TTY 扩展不需要 |
| USEUCD | NO | uchardet 编码探测库未适配（archives/ohpcd 无 recipe） |
| NETROCKS | NO | 网络协议插件依赖 samba/nfs/neon/aws-sdk 均未发布 |
| MULTIARC | NO | 归档插件依赖 libarchive（已发布但首轮收敛依赖面） |
| PYTHON | NO | Python 插件默认关闭 |
| TESTING | NO | 上游 smoke 测试需 Go 工具链 + 外网，设备不可跑 |
| LEGACY | NO | 旧版注册表支持关闭 |
| MUSL | YES | 添加 -D__MUSL__ 全局宏，对齐 musl libc 语义 |

## CMake 4.x 兼容

far2l 顶层 CMakeLists.txt 声明 `cmake_minimum_required(VERSION 3.5.0)`，设备 cmake 为 4.1.2。
通过 Conan recipe 中 `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"` 解决 E103/E187 兼容问题。

## 上游测试

far2l 官方测试位于 `testing/` 目录，包含 6 个 smoke 测试用例：
1. `0001-run-and-exit` — 启动后正常退出
2. `0002-copy-files` — 文件复制
3. `0003-move-files` — 文件移动
4. `0004-vt-shell` — VT shell 交互
5. `0005-view-file` — 文件查看
6. `0006-view-file-word-wrap` — 自动换行查看

测试框架为 Go 程序（`testing/far2l-smoke.go` + `far2l-smoke-run.sh`），测试逻辑以 JS（`tests/NNNN-*/test.js`）编写由 goja 执行，pty 交互依赖 `github.com/ActiveState/termtest`。

### 运行可行性实测（2026-08-28，二轮深排，修正初判）

逐项实测四个前置条件并按「可解决/平台硬限制」分类。**初判误报 pty 不可用，二轮深排证实 pty 全链路可用**；唯一真正死结是 Go 工具链不可执行（平台限制），其余均可解决但被 Go 死结连带阻塞：

| 前置条件 | 实测命令/证据 | 实测结果 | 性质分类 |
|---------|--------------|---------|---------|
| **Go ≥ 1.18 工具链** | `os.execv(".../go")` 捕获 errno | **EACCES (errno 13)**，PATH 内无 go；预置 `usr/local/go/bin/go`（aarch64 static ELF）execve 被拒 | 🔴 **平台硬限制（不可解决）** |
| ↳ 排除文件权限位 | `chmod 755 go` 后再执行 | chmod 成功但执行仍 EACCES | 非权限位问题 |
| ↳ 排除 noexec 挂载 | clang 编 `static_test.c`（同挂载点同 seclabel）执行 | `static ok` exit=0 — **同挂载点可执行** | 非挂载 noexec |
| ↳ 排除 seclabel/MAC | `ls -Z` 对比 go vs static_test | 两者均 `u:object_r:hmdfs:s0`，static_test 可跑 | 非 seclabel |
| ↳ 排除 cmd-pkgs 另装 | 查 cmd-pkgs releases 全量 assets | 无 go/golang 预编译包 | 无替代源 |
| ↳ 根因定位 | 排除上述 4 项后 | 内核对预置 go 二进制内容策略拒绝 execve（具体机制超出用户层可定位范围，已 3 轮止损） | 不可在用户层修复 |
| **/tmp 可写** | `touch /tmp/test` | `Read-only file system`（exit 1）；`/tmp` 只读挂载 `drwxr-xr-x 2 root root` | 🟡 **工具环境问题（可解决，被 Go 连带阻塞）** |
| ↳ 可写替代 | `touch $TMPDIR/test` | `TMPDIR=/storage/Users/currentUser/tmp` 可写 | 有替代路径 |
| ↳ 框架 patch 可行性 | `grep /tmp` 脚本+go 代码 | 仅 `far2l-smoke-run.sh:5` + `far2l-smoke.go:983` 两处硬编码，test.js 无硬编码 | 改 2 处即可指向 TMPDIR |
| **pty 设备** | C 层 `openpty()`/`open("/dev/ptmx")` | **全链路通过**：`openpty: OK (master=3 slave=4)`；`open /dev/ptmx: OK (fd=3)`；`posix_openpt→grantpt→unlockpt→ptsname→open slave` 全通 | 🟢 **可用（初判误报，已修正）** |
| ↳ 初判误报原因 | `ls -la /dev/ptmx /dev/pts/` | 返回 `Permission denied`（这是 `ls`/`stat` 的，非 `open()`） | stat 不可访问≠open 不可用 |
| **TESTING=YES 编译** | `strings far2l \| grep testing` | `Testing facilities not enabled, rebuild with -DTESTING=YES`（当前 TESTING=NO） | 🟡 **工具环境问题（可解决，被 Go 连带阻塞）** |
| ↳ 重编可行性 | 源码 `WinPort/CMakeLists.txt:50` + `WinPortMain.cpp:504` | 重编 `-DTESTING=YES` 启用 `FAR2L_TESTCTL` 命令通道（testctl socket） | 可重编启用 |
| ↳ 但 moot | smoke 框架由 Go 驱动 | Go 不可执行（见上），testctl 通道虽开也无人驱动 | 启用无意义 |

### 无法测试的最终说明

**6 个上游 smoke 测试标记为 BLOCKED，根因 = 平台硬限制（Go 工具链不可执行），非工具环境问题。**

- **真正的死结（1 项，平台硬限制，不可解决）**：Go 工具链无法执行。预置 go 二进制（aarch64 static ELF）execve 返回 EACCES，已逐项排除文件权限位、挂载 noexec、seclabel/MAC 三项常见原因（对照实验：clang 编译的 static_test 同挂载点、同 seclabel、同路径前缀可正常执行），cmd-pkgs 无 go 预编译包可另装。根因指向内核对预置 go 二进制内容的执行策略，超出用户层可修复范围。Go 是 smoke 框架的驱动语言（`far2l-smoke.go` 编译为 `far2l-smoke` 二进制驱动 6 个 test.js），**Go 死则框架死，整条测试链无法启动**。
- **可解决但被连带阻塞（2 项，工具环境问题）**：(1) /tmp 只读——`TMPDIR=/storage/Users/currentUser/tmp` 可写，框架仅 2 处硬编码可 patch 指向 TMPDIR；(2) TESTING=NO——重编 `-DTESTING=YES` 可启用 FAR2L_TESTCTL 命令通道。两者均可修复，但因 Go 驱动无法运行，修复它们无意义，故未执行。
- **误判修正（1 项，实际可用）**：pty 设备。初判据 `ls /dev/ptmx` 返回 Permission denied 判定"pty 不可用"，二轮 C 层实测 `openpty()`/`open("/dev/ptmx")` 全链路通过（master=3 slave=/dev/pts/6），证实 pty 在用户空间可用，`ls`/`stat` 不可访问 ≠ `open()` 不可用。termtest 框架用 openpty 系调用，pty 非阻塞点。

**结论**：若未来 Go 工具链在鸿蒙 PC 可执行（官方提供可执行预编译包或内核策略调整），则 /tmp patch（2 行）+ 重编 TESTING=YES 即可跑通全部 6 个 smoke 测试——pty 已就绪无额外工作。当前因 Go 死结，无可行路径。

### 上游测试用例清单（未运行，记录备查）

| 序号 | 测试名 | 测试内容 | JS 断言要点 |
|------|--------|---------|------------|
| 0001 | run-and-exit | 启动→跳过帮助→F10 退出确认→退出；二次启动无帮助；关闭退出确认+Shift+F9 存配置→无确认退出 | `ExpectString("left-fgdfgfd")`、`ExpectString("Help - FAR2L")`、`ExpectString("Do you want to quit FAR?")`、`ExpectAppExit()` |
| 0002 | copy-files | 选 5 项→F5 复制→校验左右目录哈希一致→源未变 | `HashPathes()` 左右对比、`ExpectString("════ Copy ═════")` |
| 0003 | move-files | 文件移动校验 | （同上哈希校验模式） |
| 0004 | vt-shell | VT shell 交互 | pty 终端交互断言 |
| 0005 | view-file | 文件查看（7 个 initdir 文本文件） | 查看器渲染断言 |
| 0006 | view-file-word-wrap | 自动换行查看（15 个 initdir 文本文件） | 换行渲染断言 |

### 可执行测试实测结果（2026-08-28）

上游 Go smoke 框架因 Go 工具链不可执行而无法运行，但 pty 已就绪（见上节）。故用 **Python+pty 直接驱动 far2l** 复现上游 smoke 的核心断言路径，并对 test_package 做详细重跑。实测发现：**far2l `--tty` 模式在真实 pty 下启动 ~0.2s 即 SIGSEGV 崩溃**，这是上游 6 个 smoke 全部受阻的真正根因（而非 Go 死结）。

#### 测试一：test_far2l.cpp（产物完整性，13 项 CHECK，全部 PASS）

用 `clang++ -std=c++17 -stdlib=libc++` 编译 `test_package/test_far2l.cpp` 并运行，逐项断言：

| # | 断言 | 实测 | 结果 |
|---|------|------|------|
| 1 | 二进制路径可访问 | `access(F_OK)==0` | ✅ PASS |
| 2 | 文件非空 | `size=4383296 bytes` | ✅ PASS |
| 3 | ELF 魔数 `7f 45 4c 46` | offset 0-3 | ✅ PASS |
| 4 | ELF class = 64-bit | offset 4 = 0x02 | ✅ PASS |
| 5 | 数据编码 = little-endian | offset 5 = 0x01 | ✅ PASS |
| 6 | ELF version = 1 | offset 6 = 0x01 | ✅ PASS |
| 7 | OS/ABI = SYSV | offset 7 = 0x00 | ✅ PASS |
| 8 | e_type = ET_EXEC(2) 或 ET_DYN(3) | DYN(3, PIE) | ✅ PASS |
| 9 | e_machine = EM_AARCH64(183/0xb7) | 0xb7 0x00 | ✅ PASS |
| 10 | e_entry 非零 | 入口点存在 | ✅ PASS |
| 11 | program headers 数量 > 0 | e_phnum > 0 | ✅ PASS |
| 12 | section headers 数量 > 0 | e_shnum > 0 | ✅ PASS |
| 13 | `--help` 含版本号 `2.8.0` | stdout 含 "2.8.0" | ✅ PASS |

**结论：13/13 PASS** — 产物完整性验证通过。

#### 测试二：test_far2l.sh（功能测试，7 项，全部 PASS）

| # | 测试内容 | 实测结果 | 结果 |
|---|---------|---------|------|
| 1 | 二进制存在且非空 | 4383296 bytes | ✅ PASS |
| 2 | ELF 魔数 `7f454c46` | 匹配 | ✅ PASS |
| 3 | ELF class 64-bit | offset 4 = 0x02 | ✅ PASS |
| 4 | e_machine AARCH64 `b700` | 匹配 | ✅ PASS |
| 5 | `--help` 含 `--tty`/`--norgb`/`2.8.0` | 三者均出现 | ✅ PASS |
| 6 | `--version` 输出 | `far2l, version 2.8.0...` | ✅ PASS |
| 7 | `--tty --norgb` 无头启动不 segfault/abort | exit=124(timeout 正常，非 139/134) | ✅ PASS |

原始脚本 `test_far2l.sh` 运行输出：`All tests passed`。**结论：7/7 PASS**。

#### 测试三：0001-run-and-exit Python+pty 复现（上游 smoke 等价，FAIL — SIGSEGV）

因 Go 框架不可运行，用 Python `pty.openpty()` 直接驱动 far2l 复现 0001 的断言路径：启动 `--tty --nodetect --mortal -u profile -cd left -cd right` → 期望渲染 "Help - FAR2L" → ESC → F10 → 期望 "Do you want to quit FAR?" → Enter → 期望 exit 0。

**实测结果：far2l 启动 ~0.2s 后 SIGSEGV (signal 11)，未能到达任何断言点。**

```
子进程在 0.2s 后被信号终止: SIGSIGSEGV (11)
渲染迹象: cursor_show=True clear/home=True output_size=1655
崩溃=True
```

崩溃前 pty 输出（1655 bytes）确认 far2l 已开始 TTY 渲染：输出了光标定位转义序列（`\x1b[8;H`、`\x1b[80X` 等）、清屏（`\x1b[H`）、光标显示（`\x1b[?25h`）、`CursorShape=2`，以及 profile 目录初始化日志（`SetCustomSettings`、`EnsureDir` 系列）。崩溃发生在初始化渲染阶段，远早于 0001 的任何交互断言点。

诊断对照：不加 `--norgb` 与加 `--norgb` 行为不同——test_far2l.sh Test 7 用 `--tty --norgb < /dev/null`（非 pty，stdin 为空）时 exit=124（timeout，正常存活）；而本 pty 测试用 `--tty --nodetect --mortal`（真实 pty，无 `--norgb`）时 0.2s 即 SIGSEGV。崩溃与 RGB/图形后端或 pty 输入处理相关，需 gdb 进一步定位。

**0001 各断言点实测状态：**

| 0001 断言点 | 期望 | 实测 | 结果 |
|------------|------|------|------|
| 启动渲染面板 | "left" 面板出现 | 崩溃前已开始渲染但未到达面板 | ❌ FAIL (SIGSEGV) |
| "Help - FAR2L" | Help 对话框出现 | 未到达（崩溃于初始化） | ❌ FAIL (SIGSEGV) |
| ESC 关闭 Help | Help 消失 | 未到达 | ❌ BLOCKED |
| F10 退出确认 | "Do you want to quit FAR?" | 未到达 | ❌ BLOCKED |
| Enter 确认退出 | exit 0 | exit -11 (SIGSEGV) | ❌ FAIL |

**结论：0001-run-and-exict FAIL — far2l TTY 模式存在启动期 SIGSEGV 运行时缺陷。**

#### 测试四：0002-0006 评估（全部被同一崩溃阻塞）

逐一检查 0002-0006 的 test.js 启动方式，**全部使用与 0001 相同的 `StartApp(["--tty","--nodetect","--mortal",...])` pty 启动路径**：

| 用例 | 启动方式 | 与 0001 共享启动路径 | 实测状态 |
|------|---------|---------------------|---------|
| 0002 copy-files | `--tty --nodetect --mortal -u profile -cd left -cd right` | ✅ 相同 | ❌ BLOCKED（同一 SIGSEGV） |
| 0003 move-files | 同上 | ✅ 相同 | ❌ BLOCKED（同一 SIGSEGV） |
| 0004 vt-shell | 同上 | ✅ 相同 | ❌ BLOCKED（同一 SIGSEGV） |
| 0005 view-file | 同上 | ✅ 相同 | ❌ BLOCKED（同一 SIGSEGV） |
| 0006 view-file-word-wrap | `StartAppWithSize([...], 95, 24)` 同参数 | ✅ 相同 | ❌ BLOCKED（同一 SIGSEGV） |

**结论：0002-0006 无可独立执行者**，均依赖 far2l `--tty` pty 启动存活，而该路径实测 SIGSEGV。即便修复 Go 工具链，6 个 smoke 仍全部受阻于此崩溃。

#### 可执行测试汇总

| 测试用例 | 类型 | 结果 | 说明 |
|---------|------|------|------|
| test_far2l.cpp | test_package/产物完整性 | ✅ 13/13 PASS | 二进制格式、架构、版本号验证通过 |
| test_far2l.sh | test_package/功能 | ✅ 7/7 PASS | ELF 格式 + `--help`/`--version` + `--tty --norgb` 无头启动 |
| 0001-run-and-exit | 上游 smoke/Python+pty 复现 | ❌ FAIL | far2l `--tty` 启动期 SIGSEGV，未达任何断言 |
| 0002-0006 | 上游 smoke | ❌ BLOCKED | 共享 0001 启动路径，同崩溃阻塞 |

## 已知限制与残余风险

1. **上游 smoke 测试 BLOCKED**：6 个 Go smoke 测试因三重阻塞无法运行——(a) 无可用 go 工具链（PATH 内无 go，`usr/local/go/bin/go` 存在但 Permission denied）；(b) /tmp 只读（框架硬编码 `mkdir -p /tmp/far2l-smoke/output`）；(c) pty 设备不可访问（`/dev/ptmx`、`/dev/pts/` 均 Permission denied，termtest 依赖）。实测见「上游测试」章节。
2. **/tmp 只读**：鸿蒙设备 /tmp 目录为只读（`drwxr-xr-x 2 root root` 只读挂载），far2l 运行时若尝试写入 /tmp（如临时文件、缓存）可能失败。上游 smoke 框架硬编码 `/tmp/far2l-smoke/output`，这是标记 BLOCKED 的原因之一。
3. **HMDFS 运行时风险**：far2l 的文件操作（复制/移动/查看）在 HMDFS 文件系统下可能遇到权限或行为差异。HMDFS 不支持硬链接、mkfifo 等操作，可能影响 far2l 的 pty 管理和 VT shell 交互功能。需在交付阶段进行人工运行时验证。
4. **TTY 无头测试局限性**：test_far2l.sh Test 7 验证 `far2l --tty --norgb` 无头启动不崩溃（segfault/abort 检查），但无法验证完整的 TTY 渲染和 VT 栈交互。真正的 TTY 功能验证需要交互式终端环境。
5. **uchardet 功能降级**：USEUCD=NO 关闭了编码自动探测功能，可能导致非 UTF-8 文件名显示异常。此为功能降级，非编译问题。

## 许可证

far2l 主项目许可证为 GPL-2.0。上游多组件各带独立许可证（LGPL-2.1、MIT、BSD-3-clause 等）。
multiarc 插件捆绑的 UnRAR 源码有自定义许可限制（非 OSI 自由许可），本适配通过 `-DMULTIARC=NO` 规避。

## 源码

- 官方源码 tarball：`https://github.com/elfmz/far2l/archive/refs/tags/v_2.8.0.tar.gz`
- SHA-256：`b0fddad2e3985f245f9e691e23b90fb97f7d29d9a0b131fe686aa3cbb2e4ea01`
- 解压根目录：`far2l-v_2.8.0/`
- 上游 tag：`v_2.8.0`（注意下划线前缀）
