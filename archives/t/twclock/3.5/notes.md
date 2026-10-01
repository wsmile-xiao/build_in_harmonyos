# twclock 3.5 — 适配笔记

## 软件概况
- **上游**: twclock 3.5 by Ted Williams (WA0EIR)
- **源码**: Debian 官方源 tarball `twclock_3.5.orig.tar.gz`
- **构建系统**: autotools (automake 1.16 生成)
- **产物类型**: 应用程序 (`package_type = "application"`)，单二进制 `bin/twclock`
- **许可证**: GPL-2.0-or-later

## R51 上游测试清点
- `find . -iname "*test*"` -> 0 个测试源文件
- `Makefile.in` 仅有 `check: check-recursive`（`check-am: all-am`，空 pass-through）
- 无 `test:` 目标（`make test` 报 "No rule to make target 'test'"）
- 无测试套件、无测试用例
- `build()` 内以 `timeout 300 make check` 原样执行并捕获原始输出（证据保留在构建日志），未删除、未伪造

## 适配要点
1. **Motif 依赖**: 上游无 Motif，本仓库提供 `motif/2.3.8` (`libXm.so.4` + `Xm/*.h`)，通过 `--with-motif-includes/--with-motif-libraries` 显式指定，跳过 acinclude.m4 的硬编码系统目录扫描。
2. **X11/Xt/PulseAudio 依赖**: 显式声明 `libxt/1.3.1`、`libx11/1.8.13`、`pulseaudio/17.0`、`xorgproto/2025.1`，保证干净图上头文件/库齐全。
3. **PKG_CHECK_MODULES(APPDEFS, xt)**: 需 `xt.pc`；`libxt/1.3.1` 导出 `pkg_config_name = "xt"` 并通过 `buildenv_info` 注入 pkgconfig 目录；`PKG_CONFIG_PATH` 追加 `generators_folder` 确保可见。
4. **app-defaults 目录**: 上游通过 `PKG_CONFIG --variable=appdefaultdir xt` 自动探测，但生成的 pc 可能缺此变量；配方显式传 `--with-appdefaultdir=<package_folder>/share/X11/app-defaults`，消除不确定性。
5. **交叉编译 malloc 测试**: `AC_FUNC_MALLOC` 会跑测试程序；悲观默认会把 `malloc` 重定义为 `rpl_malloc` 导致链接失败；配方钉死 `ac_cv_func_malloc_0_nonnull=yes`。
6. **E011 shell/umask 修复**: `configure` 的 `umask 077` 改为 `022`；`configure` 与 `config/` 下 helper 脚本的 `#! /bin/sh` shebang 重定向到 OHOS shell（`/system/bin/sh` 或 `/bin/sh` 等）。
7. **打包策略**: `make install` 在 OHOS/HMDFS 上不可用（`install-sh` 无执行权限、HMDFS 拒绝覆盖已存在可执行文件），采用显式 `copy()` 分级打包并逐项校验；`make install DESTDIR=...` 仍以 evidence-only 方式运行并捕获日志。
8. **Headless 现实**: 无 X server，`XtVaOpenApplication` 必然失败并打印 `Can't open display` 退出；消费者测试断言该行为，不伪造 `--version`。跨架构宿主无法真正加载 aarch64 二进制时该断言记 SKIP 而非 PASS。
9. **libxpm 兼容性冲突**: twclock 需要 Motif（强制 libx11/1.8.13 track）和 libxpm（registry binary 用 libx11/6.4.0 track）。两 track 不兼容且 libxpm recipe 强制 libx11/6.4.0。XPM 仅用于窗口图标，configure.ac 有 fallback。决定**不依赖 libxpm**，编译成功但无 XPM 图标。

## 验证结果
- `conan create` 本地通过（同源门禁脚本 `CI_PACKAGES=archives/t/twclock/3.5 zsh ci/conan/build_and_test.sh` → 退出码 0）
- 产物完整性：`bin/twclock`、`share/X11/app-defaults/Twclock`、`share/man/man1/twclock.1`、`licenses/COPYING`、`share/applications/twclock.desktop`、`share/pixmaps/twclock.png` 均存在
- ELF DT_NEEDED 链: `libXm.so.4` `libXt.so.6` `libX11.so.6` `libpulse-simple.so.0` `libpulse.so.0`（另有 `libSM.so.6` `libICE.so.6` `libc.so`）
- 运行期**递归**闭包：从 `bin/twclock` 的 DT_NEEDED 出发逐层展开，共 **12 个库**全部可从
  conanrun 注入的 `LD_LIBRARY_PATH` 解析到（无需执行二进制，任意宿主架构可验证）：
  ```
  libXm.so.4  libXt.so.6  libX11.so.6  libSM.so.6  libICE.so.6
  libpulse.so.0  libpulse-simple.so.0  libXext.so.6  libxcb.so.1
  libXdmcp.so.6  libXau.so.6  libpulsecommon-17.0.so
  ```
  其中 `libpulsecommon-17.0.so` 只存在于 `<pulseaudio>/p/lib/pulseaudio/` 子目录，
  该子目录确实出现在消费者 `LD_LIBRARY_PATH` 中（已实测），因此
  「libpulse 不可解析」**不是**搜索路径缺口。
- 消费者测试 `test_package/test_twclock.sh` 断言上限 12 项 = (a)1 + (b)5 + (c)1 + (d)4 + (e)1
  - **aarch64 OHOS 原生 worker 且加载器可用**（实测 CI #63074，worker `OpenHarmonyPCDeveloper-CI-005`）：`assertions=12 failures=0 skipped=0`
  - **aarch64 OHOS 原生 worker 但加载器拒绝加载打包库**（实测 CI #63039，worker `OpenHarmonyPCDeveloper-CI-036`）：`assertions=11 failures=0 skipped=1`，
    (c) 如实记 **NOT VERIFIED**
  - **x86_64 异构宿主（无完整 OHOS sysroot）**：`assertions=11 failures=0 skipped=1`，(c) 记 SKIP，
    **不计入断言数、不冒充证据**

### 关于 (c) headless 断言的取证纪律

历史版本的测试脚本把「动态加载器 relocation 失败」（`Error relocating ... symbol not found`）
当作 (c) 的 PASS。这属于**空壳断言**：二进制根本没跑到自己的代码，却计入了
`assertion_count`，会让「headless 打印 display 错误」这一结论失去证据支撑。
随后一版把所有加载器失败一律降级为 SKIP，这又**过头了**：它把
「本包没打全依赖」和「平台加载不了」两种完全不同的情形混为一谈，
并在健康 worker 上丢掉了本来成立的真实断言。

现行判据（以 (e) 的递归闭包为依据）：

| 二进制是否真的跑起来 | 递归闭包 | 判定 |
|---|---|---|
| 是，打印真实 Xt/display 错误 | — | **PASS**（计入断言） |
| 挂起（timeout 30） | — | **FAIL** |
| 否，加载器报错 | **不完整** | **FAIL** —— 本包交付缺陷（缺可解析依赖），不掩盖 |
| 否，加载器报错 | **完整** | **SKIP / NOT VERIFIED** —— 平台/worker 条件，回显具体不可加载的库名 |
| 异构宿主且未提供可用 `QEMU_LD_PREFIX` | — | **SKIP** |

负向对照（证明该断言有鉴别力，不是空壳）：把 `<pulseaudio>/p/lib/pulseaudio`
从 `LD_LIBRARY_PATH` 去掉后，`libpulsecommon-17.0.so` 不可解析 ⇒ (c) 与 (e) 双双
FAIL、`exit 1`；恢复后即 `TRANSITIVE_CLOSURE=complete`。

历史版本的测试脚本还硬编码过开发者机器 sysroot 路径
（`/mnt/c/Users/13909/ohos-sysroot`，实测为空目录），已移除；跨架构执行必须由
调用方显式提供 `QEMU_LD_PREFIX`。

### 关于 (e) 闭包断言的取证纪律：空走一遍也曾算 PASS

`(e)` 的原始判据只有一条：`CLOSURE_MISSING` 为空即 PASS。这在**没有真正检查过
任何库**时同样成立——若 `bin/twclock` 的 `DT_NEEDED` 解析不出任何非系统条目
（readelf 失败、二进制不可读、或依赖全被 `closure_is_system` 过滤），
遍历循环一次都不进，`CLOSURE_MISSING` 天然为空，于是打印
`PASS: runtime closure: ... resolvable` 与 `TRANSITIVE_CLOSURE=complete`，
而实际考察了 **0 个库**。这是**空壳断言**：结论与证据脱钩。

本机（WSL Ubuntu，x86_64，`/usr/bin/readelf`）用**真实 ELF** 复现，取一个
`DT_NEEDED` 为 0 的静态二进制：

| 脚本版本 | 输出 |
|---|---|
| 修改前 | `resolved:0 library/libraries` → `PASS: runtime closure: ... resolvable`，`TRANSITIVE_CLOSURE=complete` |
| 修改后 | `resolved:0 library/libraries` → `FAIL: runtime closure: VACUOUS -- DT_NEEDED walk resolved 0 libraries`，`TRANSITIVE_CLOSURE=vacuous` |

修复方式：PASS 必须由**正向证据**支撑，而不只是「没找到缺失」——

1. 遍历至少解析到 1 个库，否则判 `VACUOUS` FAIL；
2. 遍历必须覆盖 (b) 断言的那 **5 个直接 soname**，缺一即 FAIL；
3. 汇总行与断言保持一致，0 个库时输出 `TRANSITIVE_CLOSURE=vacuous` 而非 `complete`。

修复后用与 twclock 依赖拓扑同构的**真实多级 ELF 闭包**做四组对照
（`main → libXm.so.4/libXt.so.6/libX11.so.6/libpulse-simple.so.0/libpulse.so.0`，
且 `libXm.so.4 → libXt.so.6 → libX11.so.6`）：

| 对照 | 扰动 | 结果 |
|---|---|---|
| A 正对照 | 无 | `resolved:5` → **PASS**（`5/5 direct sonames covered`），`assertions=11 failures=0`，exit 0 —— **无误报** |
| B 深层缺失 | 抽走 `libX11.so.6` | `resolved:4` → FAIL，`TRANSITIVE_CLOSURE=incomplete libX11.so.6`，exit 1 |
| C 直接缺失 | 抽走 `libpulse.so.0` | `resolved:4` → FAIL，`TRANSITIVE_CLOSURE=incomplete libpulse.so.0`，exit 1 |
| D 空走 | `DT_NEEDED` 为 0 | `resolved:0` → **FAIL (VACUOUS)**，`TRANSITIVE_CLOSURE=vacuous`，exit 1 |

复现方式见 `test_package/test_twclock.sh` 头部注释；断言总数不变（(e) 仍只计 1 项），
故 `assertion_count: 12` 无需改动。

## 加载器条件的判据：为什么 CI #63039 红了而 #63074 绿了

**同一 SHA `5270206912`、同一份代码，两个 worker 结论相反**：

| 构建 | Worker | 结果 |
|---|---|---|
| #63039 | `OpenHarmonyPCDeveloper-CI-036` | ❌ 校验失败（`conan-build-test`，(c) 判 FAIL） |
| #63074 | `OpenHarmonyPCDeveloper-CI-005` | ✅ 校验通过（Conan test_package / L0 / L1 全通过） |

#63039 的原始诊断（worker 原生 aarch64，DISPLAY 未设，`timeout 30`）：
```
--- captured: headless twclock (DISPLAY unset, timeout 30) exit=127 native=1 attempted=1 ---
Error loading shared library libpulse.so.0: (needed by .../p/bin/twclock)
Error loading shared library libpulse-simple.so.0: (needed by .../p/bin/twclock)
Error relocating .../p/bin/twclock: pa_simple_new: symbol not found
```
即该 worker 上 `bin/twclock` **根本没跑到自己的代码**；`exit=127` 是加载器退出码。

**取证链（逐条排除本包责任）**：

1. **同一次运行中 X11/Motif 链全部正常加载**（无任何加载错误），只有 `pulseaudio`
   的两个库失败 ⇒ 与 twclock 的链接/打包无关。
2. **不是搜索路径缺口**（本轮新增实测）：`libpulse.so.0` 的 `DT_NEEDED` 是
   `libpulsecommon-17.0.so`，后者只存在于 `<pulseaudio>/p/lib/pulseaudio/`；而该
   子目录**确实**在消费者 `LD_LIBRARY_PATH` 中，递归闭包 12/12 全部可解析
   （见上节实测清单）。此前 notes 曾把此列为「可能原因」，现已用证据排除。
3. **已发布制品完整**：`libpulse.so.0 -> libpulse.so.0.24.3`、
   `libpulse-simple.so.0 -> libpulse-simple.so.0.1.1` 符号链接链完整。
4. **权限不是判别因素**：`libXm.so.4.0.4` / `libX11.so.6.4.0` / `libXt.so.6.0.0` 与
   `libpulse*.so.0.*` 全部同为 `750` 且同属外来 uid，而 X11/Motif 链在 CI 上加载正常。
5. **worker 间不一致**（决定性证据）：#63039 与 #63074 同 SHA 结论相反，说明这是
   **特定 worker 的加载器/运行环境条件**，不是配方或打包缺陷。

**结论**：`libpulse.so.0` 在 worker CI-036 上不可加载，属
`pulseaudio/17.0` 已发布制品 / 平台加载器在该 worker 上的行为，**超出本 PR 范围**
（不越界修改他人包、不推 main）。按 R43 如实记录并止损：不恢复空壳 PASS，
也不把「闭包完整却仍加载失败」计为本包缺陷。

**未执行项（如实记录，未伪造）**：`Can't open display` 这一行为在
**worker CI-036 上尚未被真实验证过**（被加载器问题阻断）；在 worker CI-005 上
已真实验证通过（#63074）。只要加载器可用的 worker 被分配到本 PR，(c) 即为真实断言。

## 知识收获
- twclock 3.5 是典型的 Xt + Motif 应用，依赖链完整，无隐式依赖。
- `AC_FIND_MOTIF` 宏虽老旧但通过 override knobs 可确定性满足。
- `PKG_CHECK_MODULES` 在交叉编译时需显式注入 `PKG_CONFIG_PATH`。
- `ac_cv_func_malloc_0_nonnull=yes` 是交叉编译 autotools 项目的常见钉死项。
- HMDFS 的 `chmod` 无效、`install-sh` 不可执行、`cp` 拒绝覆盖活体可执行文件，是已知平台限制（dinotrace 同款），显式 `copy()` + 校验是标准解法。
- 无 X server 时 Xt 应用的预期行为是打印 display 错误并退出，非崩溃；消费者测试应断言此行为而非伪造版本开关。

## 待办 / 风险
- 依赖 `pulseaudio/17.0` 的传递依赖（alsa-lib, dbus, libsndfile, json-c, expat, libffi, libxcb, check 等）需均已发布到制品仓；L0i 已验证 recipe 存在，binary 发布由 release pipeline 保证。
- CI 侧 `llvm-readelf` 路径为 `/data/service/hnp/bin/llvm-readelf`，本地 WSL 回退到系统 `readelf`；test 脚本已做兼容。
- 分支名 `feat/twclock-3.5` 符合 L0n 精确匹配要求。

## 阻塞项：`libxext` 制品缺口导致 CI 需源码重建（与 libxpm 同源的 libX11 轨道冲突）

本包自身配方与测试无缺陷，但 **CI 红灯的根因在依赖制品仓**，不在本包。取证如下（可复现命令附后）：

**1. twclock 依赖图强制 libX11 1.8.13 轨道**
`motif/2.3.8` 以 `force=True` 锁定 `libx11/1.8.13`；`libxt/1.3.1` → `libxext`，
因此 twclock 需要的 `libxext/6.4.0.1` 二进制包 ID 为 **`eab79208a9437a856077cc57885309d75bdb4a31`**
（`requires: libx11/1.8.Z`）。

**2. 制品仓 `ohpcd` 上 `libxext/6.4.0.1` 只有另一条轨道的二进制**
`conan list 'libxext/6.4.0.1:*' -r ohpcd` 显示已发布的唯一包 ID 为
**`e647863c487673f3505fad09e4305079038bb22d`**，其 `requires` 是
`libx11/6.4.Z` + `libxcb/1.16.Z`（旧轨道）。该二进制与本依赖图**不兼容**。

**3. 后果：每次 CI 都必须从源码重建 libxext**
CI #62842 日志：
```
libxext/6.4.0.1: Main binary package 'eab79208...' missing
libxext/6.4.0.1: Compatible configurations not found in cache, checking servers
libxext/6.4.0.1: No compatible configuration found
libxext/6.4.0.1: Building from source
```
同一次运行中 `knowledge_check.sh` 与 `junk_check.sh` 各出现一次
`fork: Out of memory`，最终在 libxext 的 configure 阶段：
```
/system/bin/sh: .../conanbuildenv-release-armv8.sh[13]: can't fork - try again
ERROR: Package 'eab79208...' build failed
```
即 **worker 内存/进程数耗尽导致 fork 失败**，而非编译错误或配方问题。

**4. 本地同源复验通过（证明配方与测试无缺陷）**
`conan create archives/t/twclock/3.5 -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl`
在本地缓存已有 libxext 二进制的前提下成功，消费者测试
`assertions=11 failures=0 skipped=1`（x86_64 宿主，(c) 记 SKIP），
`assertions=12 failures=0 skipped=0` 在 CI aarch64 原生 worker 上达成；
DT_NEEDED 实测含
`libXm.so.4 / libXt.so.6 / libX11.so.6 / libpulse-simple.so.0 / libpulse.so.0`。

**4. 最新实测：CI #63039 已能从缓存解析 libxext**（本轮复核新增）
`#63039` 的依赖图显示 `libxext/6.4.0.1#a99fc9be…` 与二进制
`eab79208a9437a856077cc57885309d75bdb4a31` 均标记为 **Cache**，
且本次构建一路走到 `package()` 与 `test_package()` 才因 (c) 失败——
即 `eab79208…` **不在** `ohpcd` 制品仓，而在 worker 本地 conan 缓存中。
因此：
- 制品仓缺口 **依然存在**（`conan list 'libxext/6.4.0.1:*' -r ohpcd` 本轮复核仍只有
  `e647863c…`，`requires: libx11/6.4.Z`），本节 1–3 条结论不变；
- 但「每次 CI 都被迫源码重建 ⇒ 必然 OOM」已被实测证伪：预热过的 worker 直接命中缓存，
  构建不再重编 libxext。`can't fork` 只出现在**冷缓存** worker 的重建路径上（如 #62842）。
- 影响：CI 结果对 worker 缓存状态敏感。冷 worker 仍有 OOM 风险，但那是依赖制品的
  发布问题，不是本包的配方/测试缺陷。

**未执行项 / 解除条件（超出本 PR 范围）**
需先为 `libxext/6.4.0.1` 发布一条 **libx11/1.8.13 轨道**（`1.8.Z`）的 OHOS armv8
二进制，使包 ID `eab79208…` 可从 `ohpcd` 直接下载；届时冷 worker 也不再需要源码重建。
本 PR 不越界修改他人包、不推 main，故在此如实记录而不伪绿。
---

**编译结束**: 2026-09-27 10:25
**最终状态**: built
