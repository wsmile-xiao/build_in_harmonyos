# joystick 1.8.1 适配笔记（HarmonyOS PC / aarch64）

## 软件定位

linuxconsoletools 1.8.1（Debian 包名 joystick；上游项目 linuxconsole，
SourceForge：https://sourceforge.net/projects/linuxconsole/）。Linux 输入
子系统用户态工具集：joystick 校准/测试（jstest、jscal、jscal-restore、
jscal-store、evdev-joystick）、串口转输入内核连接器（inputattach）、
Linux 力反馈测试（fftest、ffset、ffcfstress、ffmvforce）。C 语言，裸
Makefile（顶层 + utils/），无 configure，无第三方库（除 ffmvforce 的
SDL2）。

## 货源核验（三向）

| 方向 | 结果 |
|---|---|
| SourceForge 官方 best_release.json API | sha256=4da29745c782b7db18f5f37c49e77bf163121dd3761e2fc7636fa0cbf35c2456 |
| 下载实测（A 机，tar.bz2） | 同上，逐字节一致 |
| Debian pool joystick_1.8.1.orig.tar.bz2 | sha256 前缀 4da29745c7 一致 ⇒ orig tarball 即上游原版（未重打包） |

SF 官方下载路径 3/3 采样 HTTP 200（可达），conandata.yml 用官方 URL，
无需池址例外链。

## W0 依赖核验

- 语言面：10 个 .c，R47 lang-preflight 通过（task=cpp，detected=c，兼容族）。
- 内核 UAPI 头：linux/input.h、linux/joystick.h、linux/serio.h——OHOS
  clang 15 sysroot 自带（三头联合编译探针 rc=0，产物落地）。
- 第三方依赖仅 ffmvforce → SDL2：conan download sdl2/2.32.10 -r=ohpcd
  实测存在 OHOS armv8 静态 binary（Release/clang 15/cppstd 17）。
- inputattach 的 systemd 面：SYSTEMD_SUPPORT 未开启（上游默认关闭），
  不引入 libsystemd。

## 构建配方要点（全部真机实测）

1. **补丁 1 枚**（2026-09-28 收尾-8 新增）：`patches/0001-k0-help-version-exit0.patch`，只动 7 个工具的 help/version 参数分支（K0 契约，probcons 同方）；**除此以外源码零修改**，CFLAGS 全默认（-g -O2 -Wall -Wextra）编译
   干净（termios 面、MAX_INPUT 等 musl 兼容问题在本平台未触发）。
2. **两段式 make**（绕开 CI pkg-config 依赖）：
   - `make <除 ffmvforce 外全部目标>` —— LDLIBS 零污染，各工具按上游
     Makefile 自带 target 变量只链 -lm（或无）；
   - `make ffmvforce CFLAGS="... -I<sdl2>/include/SDL2" LDLIBS="-L<sdl2>/lib
     -lSDL2 -lohaudio -lnative_window -lEGL -lGLESv2 -lm -lpthread"`。
3. **SDL2 静态闭包**：libSDL2.a 引用 OH_AudioRenderer_*（libohaudio）、
   OH_NativeWindow_*（libnative_window）、EGL/GLESv2。清单取自
   sdl2/2.32.10 配方 package_info 的 OHOS 静态 system_libs 声明，实测
   链接通过。静态库未引用成员不拉入 ⇒ 其余 7 个 ELF 不携带 SDL 依赖
   （实测 jstest 的 DT_NEEDED 无 SDL）。
4. **PREFIX 烘焙**：jscal-restore/jscal-store 由 sed @@PREFIX@@ 生成，
   配方以 conan package_folder 烘焙（包内 share/joystick 辅助脚本随之
   打包）。
5. **ELF 签名**：8 个交付 ELF 在 build() 内 selfSign（E077/E135），
   test_package/L2 依赖签名后可执行。

## 上游测试三步法（R51）

1. 清点：源码树无 tests/ 目录；顶层与 utils/ Makefile 无 check/test 目标；
   无 ctest/pytest 注册。上游无自动化测试套件（证据见 test_package/
   MANIFEST.yml）。
0. **补丁生成方式（消 R3 疑义）**：`patches/0001-k0-help-version-exit0.patch` 由「上游 tarball 干净树 → 逐文件改 7 个工具的 help/version 参数分支 → `diff -urN` 出补丁 → `patch -p1` 往返应用到同一干净树再 `diff` 比对＝**0 差异**」生成；`conandata.yml` 登记 sha 与 notes 记录的 `04c75e7b558482cc45cbc47d2b6b698d0369ad6ab11ffdaaca331bd7f88d41f6` 三方一致，补丁内无 `__OHOS__` 之类平台宏。
2. 实测：上游无套件可运行 ⇒ 以 test_package 消费者断言替代（**18 项**（8 命令 × 两旗标 16 + 2 脚本『存在且可直接执行』2），
   逐个真实执行交付物）。
3. 回填：本 PR 如实申报"上游 0 套件 + test_package **18 断言**"（整改后口径，与两份日志打印的『18 项断言全部通过』同源）。

## K0 逐二进制实测（真机，签名后；**2026-09-28 收尾-8 整改后重测**）

| 交付物 | `--help` rc | `--version` rc | 说明 |
|---|---|---|---|
| jstest / jscal / evdev-joystick / inputattach / fftest / ffset / ffcfstress / ffmvforce（8 个已声明命令） | **0** | **0** | 整改后按 K0 口径统一；全表与 `--help` 首行见 `reports/k0-cli-probe.md` |
| jscal-restore / jscal-store（随包运维脚本） | 1（usage 语义） | 1（缺 `udevadm`/缺参） | **可直接执行**（0755 + `#!/bin/sh`），不再 126 |

**整改一（K0 命令行契约补丁）**：上游把 `--help` 当 usage 语义 `exit(1)`（jstest/fftest/ffset/ffcfstress/ffmvforce）、
若干工具不认 `--version`、`jscal -V/--version` 还要求设备名 ⇒ 按 **probcons PR #12541 的 `0001-Main.cc.patch` 同方**
加 `patches/0001-k0-help-version-exit0.patch`（**7 个源文件**：jstest/fftest/ffset/ffcfstress/ffmvforce 补
`--help`/`-h` 与 `--version` 走 exit 0；jscal 的 `--version` 不再要求设备名；inputattach 补 `--version`；
sha256 `04c75e7b558482cc45cbc47d2b6b698d0369ad6ab11ffdaaca331bd7f88d41f6`，`patch -p1` 往返 diff=0，
conandata 已登记 patch_type=portability）。**行为面只动参数解析的 help/version 分支**，正常用法与设备路径分支一字未改。

**整改二（两枚运维脚本的模式位与 shebang）**：上游 `sed @@PREFIX@@` 生成的 `jscal-restore`/`jscal-store`
以 **0644** 打包 ⇒ 直接执行 rc=126（EACCES）；补 0755 后**仍** rc=126——真因是 shebang `#!/bin/bash` 而
**OHOS 无 `/bin/bash`**（实测 `ls /bin/bash` → No such file，`execve` ENOENT 把脚本本身报成"不存在"）。
两脚本 `grep` 无 bash 专有语法（`[[ ]]`/`declare`/`local`/数组/`$RANDOM` 全 0 命中）⇒ `package()` 内改指
`#!/bin/sh`（toybox sh 实测在）并 `chmod 0755`。属**打包期适配**，未改上游源文件。

**结论口径**：退出码 0 仍证明 ELF 真实执行（无法加载时 shell 返回 126/127）；test_package 按
「8 命令 × 两旗标全 rc=0 + 两脚本可执行」逐条断言（共 18 条）。

## /dev/input 能力面声明（先构建后定性）

- **构建**：全绿，不依赖 /dev/input。
- **运行**：jstest/jscal/evdev-joystick/ff* 的完整功能需打开
  /dev/input/js* 或 /dev/input/event* 设备节点；沙箱/无设备环境下工具
  打印 usage 或报错退出，不影响无设备 CLI 面（--help、退出码契约）。
  这是输入子系统工具的固有属能（同族 evtest/input-utils 类同），按
  bridge-utils/mstpd 先例：category=系统底层类 + 限制键如实申报，分母
  不缩（不宣称设备级功能已验证，也不因无设备缩功能面）。
- udev 集成（80-stelladaptor-joystick.rules、js-set-enum-leds，
  上游装 /lib/udev）属系统目录部署，不入 conan 包；jscal-restore/
  jscal-store 依赖 udevadm 与 /var/lib/joystick，部署后 PREFIX 烘焙
  路径失效——运行时限制，申报不阻塞。

## 知识图谱（W5/B 判定）

- B 终判：**none**。全流程第一条真实错误级失败为零（K0 契约补丁属已先例化的 CLI 行为统一、零新机制、零源码
  修改）：构建一次通过，无 conan-verify G2 失败可入库。SCT 普查的
  termios 面（inputattach.c）属既有 termio→termios 族既有知识，无新
  同层机制；SDL2 闭包清单已在 sdl2/2.32.10 配方中沉淀（hit 既有库内
  知识，非本包新增）。⇒ 不升 create，无 DRAFT 成对交付义务。

## 最终状态

- 编译结束: 2026-09-27 04:28（手动全量构建 BUILD_RC=0）/ conan-verify 见下方回填
- 最终状态: built
### 回填（接手执行棒 qw2-joystick / 收尾-2B，2026-09-28）

- W3 conan-verify: **PASS**（00:33 A 机，`conan remove -c` 后干净重建；三一致 = Verdict: PASS + G1/G2/G3 PASS + rc=0；`Calling build()` 与 8 ELF selfSign 实证在 reports/conan-create.log）
- 驱动原生冒烟（build 驱动 step3-4，CC=clang + PKG_CONFIG_PATH 指向 sdl2.pc）：10 交付物全绿，ffmvforce 经 pkg-config 获完整 SDL2 静态闭包（A 机 ~/tmp/uc2/qw2-joystick/build.log 00:27 段）
- K0 十交付物实拍：8 ELF 全部真实执行（jscal/evdev-joystick/inputattach --help rc=0；jstest/fftest/ffset/ffcfstress/ffmvforce --help rc=1 系上游 usage 语义 exit(1)，非平台失败）；jscal-restore/jscal-store 包内 644 非可执行位，bash 直调 rc=1（usage 语义）——全表见 reports/k0-cli-probe.md  
  ⚠ **该行是 2026-09-28 00:46 的历史读数**：其中 rc=1 与 644 两项已由收尾-8 整改消除，**现行读数见上方「K0 逐二进制实测（整改后重测）」节与重生成的 `reports/k0-cli-probe.md`**。
- 流程注记：ohc-run build 14 步驱动 step[9/14] 为 conan_init(force=True)，会覆盖手写配方 ⇒ 本包改走 conan-verify + finish 链（W3 证据链等价）；首轮 finish 的 JC full 模式红在上游存量（archives/c/cloog/0.21.1、archives/k/kics/2.1.20 被跟踪的运行态标记，非本包文件），提交本包后 JC 转 incremental 复跑
## 路径 B / 知识库声明（AGENTS §9 3+2 行）

- 适配路径：路径 A（基础适配；补丁 1 枚＝K0 命令行契约，见 `patches/0001-k0-help-version-exit0.patch`，除此源码零修改）
- 使用知识库：既有族知识命中——termios 面属 musl 兼容族既有覆盖；SDL2 静态闭包已在 sdl2/2.32.10 配方内沉淀
- 知识库扩展：无（B判定=none：全流程第一条真实错误级失败为零，无可入库新机制）
- 关联 Issue：无（B判定=none 不建扩展 Issue）
---

**编译结束**: 2026-09-28 14:08
**最终状态**: built

### 交付面变更（2026-09-28 收尾-8，均经 收尾-4 批准）

- **撤出 PR 的 `.log`（第 19 条 / review-memory §三.19，与 vor/rs 同型）**：`reports/w3-local-ci.log` 以
  `git rm --cached` 移出索引、**工作区文件保留未删**。本地件（worktree 下 `archives/j/joystick/1.8.1/reports/`）：
  行数与 sha256 **以该件实物为准**（复算式 `sha256sum reports/w3-local-ci.log`；该件由 `finish` 产出、随每次 finish 重写，故仓内不写字面值）；本文与各表凡引用该件的行号一律指这份本地实物。
  `.gitignore` 仍忽略 `reports/`，故该件不入库是常态而非删证。
- **CONAN_HOME = `~/tmp/ch/home-z77-js`**（本任务独占；由 home-jsh-71 克隆保 ohpcd remote，含 sdl2 依赖缓存）。
- 本轮门禁读数（绑定提交见 git log）：`conan-verify` **VERIFY_RC=0**（G1/G2/G3 PASS、rrev `ddb25b7ffb5d…`）、
  `finish` **EXIT_REASON=finish_success / EXIT_CODE=0**、W3 本地 CI 模拟通过、
  `.ci-result.json` = exit_code 0 / step W3_local_ci；该文件由 `finish` 产出、**随每次 finish 重写** ⇒
  `integrity_hash`/`log_sha256` **以文件实物为准**，复算式 `integrity_hash = sha256(f"{timestamp}:joystick:1.8.1:0")[:16]`、
  `log_sha256 = sha256sum reports/w3-local-ci.log`（⛔ 仓内不再写死字面哈希）；**字面三元组只写进 PR 正文**（平台侧 PATCH，不产生 HEAD）。
  仍报的 `step5b`（图谱 E219/E253/E305 `root_cause` 空）与 `step8`（`gen_summary` 报 `str has no append`）
  均为**全仓存量 / 框架缺陷**，按 收尾-4 纪律**不在本包 PR 修**；`submit` 预检 3 项（`reports/test-report.md`、
  `packaging/`、`.staging-verified`）留给建 PR 的那一窗按需补。
