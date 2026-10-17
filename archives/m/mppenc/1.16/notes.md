# mppenc 1.16 适配笔记（主理-30，2026-09-25）

## 软件概述
- Musepack SV7 无损音频编码器 CLI（mppenc），上游主页 https://www.musepack.net/
- 源码：Debian 池 orig.tar.gz（119,335 B，sha256 228ede067c9d2e86d57ebaa8c5a578d6416afb6e1c3033874bfe2a89b84af979，实测 200）
- 构建系统：cmake（上游声明 cmake_minimum_required 2.4）；c 语言 21 个编译单元；零外部依赖（仅链接 libm）
- 源 URL 说明：任务简报指定并实测可用的 Debian 池权威镜像源（.orig.tar.gz 为上游原始打包；仓内 307 个 conandata.yml 同域先例）
- 语言预检（R47）：task=c，detected=c（21 个 c 源，占比 100%，构建系统证据 `project(mppenc C)`）→ 匹配通过

## 上游测试面清点（R51）
- 上游 tar 包 36 文件清点：无 tests/ 目录、无 ctest/pytest 注册、CMake 无测试目标 ⇒ 上游测试 = 0（上游无测试面）
- 以消费侧真实执行冒烟替代：生成 44.1 kHz/16bit/单声道 PCM WAV（0.1 秒 440 Hz 正弦），实际编码一轮并校验输出头

## 测试五维账本（与 manifest.yaml test_results、test_package/MANIFEST.yml、conan-create.log 四处同源）
| 维度 | 数量 |
|---|---|
| 上游静态测试面（tests 目录/ctest 注册） | 0 |
| 消费侧可执行断言 | 4 |
| 通过 | 4 |
| 跳过 | 0 |
| 失败 | 0 |

断言清单（SMOKE PASS=4）：
1. `mppenc --help` 退出码 0（K0）
2. `mppenc --quality 5 input.wav output.mpc` 编码退出码 0
3. output.mpc 存在且大小合理（32 B < size < 100 KB）
4. 输出头 4 字节 = 'MP+' + 流版本字节 7（SV7）

驱动构建产物先行实测（探索阶段证据）：44.1 kHz/0.1 s WAV → 2956 B output.mpc，头 4 字节 `4d 50 2b 07`，Profile 'Standard'，rc=0。

## 关键适配点（症状/根因/方案）

### 1. K0：--help 上游返回 1
- 症状：main() 对 -h/-?/--help 与 --longhelp 打印用法后 `return 1`；无 --version 选项。K0 要求主命令对 --help/--version 之一 rc=0
- 根因：2004 年代上游 CLI 未按惯例让 --help 返回 0
- 方案：最小源码补丁 `patches/0001-help-exit-zero.patch`（两处 return 1 → return 0，BEGIN/END 标注，无平台宏，PF5 合规）；沿 feat/probcons-1.12 同族先例（Issue #3354）；主命令名 mppenc 与包名一致，无需包装入口
- K0 合规：--help rc=0 实测通过（冒烟断言 1）

### 2. bionic 缺 glibc 头 fpu_control.h（首条编译错误）
- 症状：`src/mppdec.h:108: fatal error: 'fpu_control.h' file not found`（clang 15，aarch64-linux-ohos）
- 根因：mppdec.h 按 `#if defined __linux__` 包含 fpu_control.h；bionic 同样定义 __linux__ 但无此 glibc 专有头；真正的使用点 tools.c Init_FPU 已有 `__i386__ && _FPU_GETCW && _FPU_SETCW` 宏守卫（aarch64 本就不编译）
- 方案：`patches/0002-src-mppdec.h.patch（refresh-patch --auto 重生成名；手写时代名为 0002-fpu-control-glibc-guard.patch）`——include 条件改 `defined __linux__ && defined __GLIBC__`（libc 特性判别，非平台宏，PF5 合规）

### 3. 运行时段错误：const 查找表被 clang 放入只读 .rodata（★新知识，已沉淀草稿）
- 症状：编译通过后任何编码路径（含 /dev/null 输入）立即 SIGSEGV；gdb 因平台 ptrace 受限不可用（E046 族），改插桩二分定位到 Init_FastMath 首次表写入
- 根因：fastmath.c 四张查找表（tabatan2/tabcos/tabsqrt_ex/tabsqrt_m）声明为 `const float` 且无初始化器，Init_FastMath 运行时填充。老 gcc 把无初始化 const 表放入可写 .bss（历史上侥幸可用）；clang 将全零 tentative definition 优化进只读 .rodata，首次写入即段错误
- 方案：`patches/0001-src-fastmath.c.patch（refresh-patch --auto 重生成名；手写时代名为 0003-fastmath-tables-drop-const.patch）`——fastmath.c 定义与 mppenc.h 的 4 个 extern 声明一并去 const（带 BEGIN/END 注释说明，PF5 合规；其他 const 表如 Butfly 均带编译期初始化器，不受影响，保持原样）
- 知识沉淀：`knowledge/drafts/DRAFT-BCFF-const-table-rodata-segfault.kv` + `.md`（待 promote），通用机制：**const tentative definition + 运行时填充 = clang 只读段崩溃**

### 4. termios 探针族 #5（原始模式按键检测）
- 症状：keyboard.c 与 mppenc.c 各有一段 tcgetattr/tcsetattr 原始模式按键检测代码
- 根因：两段均包在 `#ifdef USE_TERMIOS` 条件编译内（Windows 走 conio.h，非 Windows 未定义 USE_TERMIOS 时回退 no-op 宏）
- 判定：src/CMakeLists.txt 的 add_definitions 仅 `-DMPP_ENCODER -DFAST_MATH -DCVD_FASTLOG`，未定义 USE_TERMIOS ⇒ **默认构建不编译 termios 代码**；属上游可选特性而非交互 UI 硬依赖，不收缩、不打补丁，源码原样保留
- 行为申报：编码中按键轮询（CheckKey/select/read stdin）在非 tty 环境直接返回不阻塞；冒烟在无终端的 conan test 环境实际执行通过

### 5. CMake 4.x 兼容
- 上游 cmake_minimum_required(VERSION 2.4)；设备 cmake 4.1.2 对 <3.5 硬报错
- 方案：CMakeToolchain 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（无补丁；仓内 airspyone-host/1.0.10、alacenc/0.4.1 等既有实践）

### 6. 源码年代兼容点（如实申报，未改动）
- src/config.h 写死 ENDIAN=HAVE_LITTLE_ENDIAN：aarch64 小端，正确
- HAVE_IEEE854_LONGDOUBLE 假定 x87 80-bit long double；aarch64 long double 为 128-bit quad，仅影响 AIFF 浮点输入头解析的极端路径，WAV 主路径无影响（冒烟已覆盖主路径）
- 上游 CMakeLists 用 `set(CMAKE_C_FLAGS "-O2 -ffast-math -fomit-frame-pointer -pipe")` 覆写标志变量：本轮实测不阻碍 OHOS 交叉编译（conan create 与驱动构建均通过），保持上游原样

## 路径 B 声明（3+2）
- 适配路径：路径 A（直接适配）+ 路径 B 判定 = create（新增通用机制：const 运行时填充表 → clang 只读 .rodata 段错误，见知识草稿）
- 使用知识库：feat/probcons-1.12 先例（K0 --help 退出码最小补丁模式，Issue #3354）；E526（补丁经 conan apply_conandata_patches/patch_ng 应用）；CMAKE_POLICY_VERSION_MINIMUM=3.5 兼容模式（airspyone-host/1.0.10、alacenc/0.4.1 既有实践）
- 知识库扩展：DRAFT-BCFF-const-table-rodata-segfault——上游 const 无初始化器表运行时填充，老 gcc 落可写 .bss 而 clang 落只读 .rodata，首次写入 SIGSEGV；定义+extern 成对去 const 修复；kv/md 成对随本 PR 待 promote
- 关联 Issue：#3364（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3364）

## 申报数据同源声明
- assertion_count=4：本账本、test_package/MANIFEST.yml、1.16/manifest.yaml test_results、conan-create.log SMOKE PASS=4 四处同源

## 补记（Staging 门禁反馈，2026-09-25）
- 驱动 Staging 校验要求 `--version` rc=0（L2 冒烟固定探 --version）；上游无 --version 选项 ⇒ 按 probcons-1.12 先例将 0001 补丁扩展为三段：--help rc=0、--longhelp rc=0、新增 --version 分支（打印版本 banner 后 rc=0，复用 About 串）。实测 VERSION_RC=0。
- K0 判定升级为 --help 与 --version 双合规；conan-create 冒烟断言 1 不变（--help rc=0）。

## 补记（收尾流水线反馈，2026-09-25）
- make check：上游无 check 目标（无测试面，见上文清点），失败属预期，非平台/真实 bug
- 驱动 Staging 校验要求 --version rc=0 ⇒ 0001 补丁扩展为三段（--help/--longhelp rc=0 + 新增 --version 分支，复用 About 串），实测 VERSION_RC=0
- finish 的 refresh-patch --auto 按基线 diff 将三个手写命名补丁重生成等价四文件自动补丁（含 BEGIN/END 标注与 --version 段，已核验无插桩残留）；conandata.yml 与 manifest.yaml 已对齐四文件命名，语义与手写版一一对应
- 驱动 Step9 conan-init(force=True) 重生成手写配方时崩于框架侧模板 license 解析（scripts/ohc/conan_recipe.py TypeError: replace() argument 2 must be str, not dict）——框架问题，非配方问题；配方验证以 conan-verify/finish W3 权威门禁为准（均通过）

## 补记（审计 r1 后）

- 证据留存订正：早期手写补丁轮次的原始 conan-create.log 已被 refresh-patch --auto 重生成轮覆盖（log_sha256 adf4b6e4… 所指件不在盘面）；W4 独立审计 r1 在干净上游全链路复跑（conan create + test_package）rc=0、SMOKE PASS=4/4、输出 2956B，复跑日志存 `~/tmp/uc2/z30-mppenc/audit-conan-create-r1.log`，作为本轮有效证据替代；manifest 所记 log_sha256 为 05:56 finish 轮读数，与现盘面 w3-local-ci.log 对应。
- 本节补记由主理-30 于审计 r1 后落盘（P3：关键适配点小节的手写时代补丁名已在本补记标注改名对应）。

---

**编译结束**: 2026-09-25 05:56
**最终状态**: built

（收尾两行由主理-30 依最终轮 `finish` 真实读数转写：时间取 `.ci-result.json` timestamp `2026-09-25T05:56:16`、状态取 `manifest.yaml` `status: built`；finish 原回写块在 refresh-patch --auto 对齐轮（a3f006233e）丢失，本转写未改任何读数。）
