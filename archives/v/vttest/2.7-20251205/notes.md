# vttest 2.7-20251205 适配笔记

## 编译环境
- 构建系统: autotools (configure + make；conan 下为 build folder 的 VPATH 构建，探索阶段为 in-source)
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18, 默认目标 aarch64-linux-ohos)
- Conan: 2.29.1 (OHOS-adapted) + profile `ohos-aarch64-device`
- 验证设备: HarmonyOS PC aarch64 真机 (HongMeng Kernel 1.12.0, 3120x2080)
- 状态: built

## 软件简介
vttest 是 Thomas E. Dickey 维护的 VT100/ANSI 终端兼容性测试程序（源自 Per Lindberg
1985 年的版本）。运行在被测终端上，通过菜单驱动地输出转义序列与测试图案，检查
光标移动、字符集、双宽/双高、颜色、键盘与鼠标报告、设备应答、VT52/VT220/VT320/
VT420/VT520 及 xterm 扩展是否符合 DEC/ANSI 规范。纯 C + POSIX tty API，无外部库
依赖，产物为 `bin/vttest` 与 `share/man/man1/vttest.1`。

## 版本号说明
上游 `patchlev.h` 标识 `RELEASE 2 / PATCHLEVEL 7 / PATCH_DATE 20251205`，发行
tarball 名为 `vttest-20251205.tgz`（上游归档站按日期发布快照）。Conan 包版本取
`2.7-20251205`，与任务版本号一致。

## 上游测试结构（R51 清点）
1. 官方 tarball 内**没有** tests/、test/ 或任何测试脚本/基准数据；MANIFEST 逐项
   列出全部发行文件（init-build 基线指纹 66 个文件），无测试资产——vttest 本身
   就是"终端测试程序"。
2. `makefile.in` 没有 check/test 目标（grep 无命中），`configure.in` 仅做编译特性
   探测（AC_HAVE_HEADERS/FUNCS、CF_* 宏），未注册任何测试程序，不存在可执行的
   `make check`。
3. vttest.1 明确说明用例由操作者驱动："The program is menu-driven ... To run a
   given menu-item, you must enter its number"，没有预期输出基准与自动化断言。
4. 结论：**上游自动化用例数 N=0**。

依据竞赛规则 6 / R51，本适配在 test_package/ 中补全消费者回归（9 条断言，含
PTY 交互冒烟），并在 PR 中如实申报（0 上游用例 + 9 条鸿蒙特有/消费者断言）。

## 编译步骤

```bash
# 1. 官方 tarball 解压（conan source()，strip_root）
# 2. 应用 patches/0001-config.guess.patch（HarmonyOS 识别 + 探测目录 umask）
#    与 patches/0002-configure.patch（config.status 临时目录 umask 077 → 022）
# 3. AutotoolsToolchain 生成环境（CC/CXX/CFLAGS/LDFLAGS 等）
# 4. ./configure && make（VPATH 构建）
# 5. make install DESTDIR=<package_folder>
```

探索阶段（设备手动编译，in-source）：

```bash
./configure --prefix=$DEFAULT_PREFIX && make -j1 && make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./configure` 直接失败：`config.guess: unable to guess system type` → `configure: error: cannot guess build type; you must specify one` | 上游 config.guess（GNU 2025-07-10）的 `case $UNAME_SYSTEM` 不含 HarmonyOS，而设备 `uname -s` 返回 `HarmonyOS`（`uname -r` 为 `HongMeng Kernel 1.12.0`）（知识库 E160） | `patches/0001-config.guess.patch`：`Linux\|GNU\|GNU/*` 情况加入 `HarmonyOS`（沿用同一套 LIBC 探测），并新增 `aarch64:HarmonyOS:*:*` → `aarch64-unknown-linux-$LIBC` 分支；原生构建因此正常识别自身，无需 `--host`（上游 config.sub 已认识 `linux-ohos`，若显式传 host 三元组也可行） |
| 2 | config.guess 编译器探测目录 `can't create .../cgXXXXXX/dummy.c: Permission denied` | config.guess 的 `set_cc_for_build()` 用 `(umask 077 && mktemp -d "$TMPDIR/cgXXXXXX")` 建探测目录；HMDFS 对 umask 077 新建目录强制 setgid（`drwx--S---`），owner 也不可写（E011） | 同一补丁内把 config.guess 三处 `umask 077` 改为 `umask 022` |
| 3 | 未打补丁的 configure 实测：`config.status` 报 21 处 `Permission denied`（`csXXXXXX/undefs.sed`、`csXXXXXX/out`、`csXXXXXX/config.h` 等均无法写入）、`config.h` **未生成**，随后 `make` 以 `No rule to make target '.1', needed by '.txt'. Stop.` 失败；打补丁后同样命令 0 处 Permission denied、`config.h`（3140 字节）正常生成、`make` rc=0 | 同 #2 的 HMDFS umask 077 机制，configure 生成的 config.status 内联脚本用 `(umask 077 && mktemp -d "$TMPDIR/csXXXXXX")` 建临时目录（E129/E112/E136） | `patches/0002-configure.patch`：configure 内两处 `umask 077` → `umask 022`（与已合入的 a52dec/0.7.4、teseq/1.1.1 同款补丁） |
| 4 | `make install` 时 GNU make jobserver 报 `mkfifo ... Operation not permitted` | OHOS/HMDFS 不允许 make 在 `$TMPDIR` 创建 jobserver fifo（仅告警，make 自动退化为单进程，构建产物不受影响） | 无需修复；记录为平台限制。CI/本地均只出现告警，构建与安装成功 |
| 5 | vttest 用管道运行会 `Cannot initialize tty modes!` 退出 | vttest 启动时 `init_ttymodes()` 会 `close(2); open("/dev/tty")`，交互菜单从 fd 0 读取；无控制终端时无法运行 | test_package 的消费者回归分两层：CLI 断言（-V/用法/man page、无需 tty）+ `pty_smoke.py` 在真正的伪终端上启动程序、等待主菜单、选择 Exit 并要求 0 退出（无 /dev/ptmx 的宿主显式 skip 77，不伪装通过） |

## 源码修改
- `patches/0001-config.guess.patch`：config.guess（2025-07-10）——
  1) `case $UNAME_SYSTEM` 的 `Linux|GNU|GNU/*)` 分支加入 `HarmonyOS`；
  2) 新增 `aarch64:HarmonyOS:*:*)` → `GUESS=$UNAME_MACHINE-unknown-linux-$LIBC`；
  3) `set_cc_for_build()` 内三处 `umask 077` → `umask 022`。
- `patches/0002-configure.patch`：configure（Autoconf 2.52.20250126 生成的文件）内两处
  `(umask 077 && ...)` → `(umask 022 && ...)`（config.status 临时目录机制）。
- 两个补丁均不改 C 源码、不注入 `__OHOS__`/`-D__OHOS__`；改动均为上游发行文件
  的平台识别/权限处理，可用 POSIX 兼容方式说明（config.guess 是上游用于识别
  平台的脚本，HarmonyOS 是其缺失的真实系统分支）。

## 依赖版本
- 运行时依赖：无（纯 C + POSIX tty API，仅 libc）
- 构建依赖：无（autoconf 生成的 configure 随 tarball 发布，不需要 autoreconf）

## 验证结果

```bash
# 1) W3/conan-verify（G0–G4 全 PASS）
$ python3 scripts/ohc-run.py conan-verify vttest 2.7-20251205 --profile ohos-aarch64-device
✅ G1 配方完整性 PASS; G0 预构建评估 PASS（命中 E490 提示，非阻塞）;
   G2 conan create PASS; G3 系统同名库隔离 PASS; G4 产物完整性 PASS
✅ 配方验证通过: vttest 2.7-20251205
   报告: archives/v/vttest/2.7-20251205/reports/conan-verify-report.md

# 2) 本地 CI 门禁（与平台 CI 同脚本，profile ohos-aarch64-device）
$ CONAN_PROFILE=ohos-aarch64-device CI_PACKAGES=archives/v/vttest/2.7-20251205 \
    zsh ci/conan/build_and_test.sh "$CI_PACKAGES"
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L1e Negative test confirmed — test genuinely depends on vttest（移除 bin/ 后 test() 失败）
L2_RESULT=skip: vttest version/help failed（vttest 只支持 -V，脚本探测的 --version/--help 非上游接口；非阻塞）
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
→ 1/1 成功

# 3) G0 干净构建复现（clean-verify：官方 tarball + 2 补丁 → configure → make → make install）
$ python3 scripts/ohc-run.py clean-verify vttest 2.7-20251205
✅ G0: 2 个补丁全部应用成功 → configure 成功 → make 成功 → make install 正常 (1 bin, 0 lib)
✅ G0 干净构建验证通过

# 4) conan create 的 test_package 逐条实跑（reports/conan-create.log）
RUN: test -x <pkg>/bin/vttest                                   → PASS
RUN: vttest -V | grep -Fx "VT100 test program, version 2.7 (20251205)" → PASS
RUN: vttest -V > /dev/null                                      → rc=0
RUN: vttest -Z 2>&1 | grep -F "Usage: vttest"                   → "Usage: vttest [options] [24x80.132]"
RUN: ! vttest -Z > /dev/null 2>&1                               → 非零退出确认
RUN: test -s <pkg>/share/man/man1/vttest.1                      → PASS
RUN: python3 pty_smoke.py <pkg>/bin/vttest
     → PTY smoke test passed: banner + main menu + clean exit (status 0, 827 bytes)

# 5) 独立 staging 回放（tarball + 补丁 → 构建 → 安装 → 运行）
$ tar xzf vttest-20251205.tgz; patch -p1 < 0001; patch -p1 < 0002   # 两个补丁 dry-run 干净
$ ./configure --prefix=... && make -j1 && make install DESTDIR=...
$ stage/.../bin/vttest -V → VT100 test program, version 2.7 (20251205)  (rc=0)

# 6) 补丁必要性对照实验（同一解包目录，唯一区别是是否应用 0002-configure.patch）
未打补丁：configure rc=0 但 config.status 报 21 处 Permission denied、config.h 未生成，
          make → "No rule to make target '.1', needed by '.txt'.  Stop."（rc=2）
打补丁后：0 处 Permission denied、config.h 3140 字节、make rc=0、./vttest -V 正常
```

## test_package 设计（消费者视角回归，9 条断言）
vttest 无编译期 API（命令行工具），test_package 直接以消费者身份执行包内二进制：
1. `bin/vttest` 存在且可执行；
2. `vttest -V` 精确输出上游版本横幅 `VT100 test program, version 2.7 (20251205)`；
3. `-V` 退出码为 0；
4. 未知选项 `-Z` 打印 `Usage: vttest` 用法文本（负向对照）；
5. 未知选项退出码非 0（负向对照）；
6. `make install` 的 man page `share/man/man1/vttest.1` 存在且非空；
7. `pty_smoke.py`（PTY 交互，3 条内部断言：版本横幅、主菜单 `Choose test type:`、
   选择 Exit 后退出码 0）——vttest 的核心功能面只有真终端能驱动；宿主无
   `/dev/ptmx` 时脚本输出 `SKIP:` 并返回 77（显式跳过，不伪装通过）。

## 对话记录

### 对话 #1（2026-09-21，人工协作）
- 人工认领任务 #11773（vttest 2.7-20251205，分支 feat/vttest-2.7-20251205）。
- 人工维护设备反向 SSH 隧道与物理设备唤醒/解锁，保证真机编译与验证连续执行。
---

**编译结束**: 2026-09-21 22:58
**最终状态**: built
