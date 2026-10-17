# vttest 2.7-20251205 测试报告

> **项目**: vttest 2.7-20251205（VT100/ANSI 终端兼容性测试程序）
> **测试日期**: 2026-09-21
> **测试环境**: HarmonyOS PC aarch64 真机（HongMeng Kernel 1.12.0，clang 15.0.4 / OHOS SDK 26.0.0.18，Conan 2.29.1）
> **测试类型**: 上游无自动化测试套件（N=0）；消费者回归（test_package，含 PTY 交互冒烟）+ G0 干净构建复现（clean-verify）+ 独立 staging 回放

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游自动化测试总数 | 0 | — |
| 新增消费者断言总数 | 9 | 100% |
| 通过 (PASS) | 9 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **9/9（100%）**

> 上游测试说明：vttest 本身即"终端测试程序"，上游不提供自动化用例与预期输出
> 基准（makefile 无 check 目标，tarball 无 tests/ 目录，vttest.1 说明用例由操作者
> 在终端上驱动）。清点证据见 `test_package/MANIFEST.yml`。依据竞赛规则 6 / R51，
> 本适配补全消费者回归断言并如实申报。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过** —— 包内二进制在 OHOS 真机可执行、版本横幅精确匹配上游
（`VT100 test program, version 2.7 (20251205)`）、错误输入按文档以用法文本 +
非零码拒绝、man page 随 `make install` 安装；PTY 交互冒烟证明 vttest 能在真实
伪终端上启动主菜单并干净退出。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| L2 冒烟脚本探测 `--version/--help`：vttest 上游只提供 `-V` | CI L2 记录为 skip（脚本声明非阻塞，非产品缺陷） | 🟢 |
| GNU make jobserver fifo 在 HMDFS 不可创建 | 仅告警，make 退化为单进程，构建/安装成功 | 🟢 |

### 2.3 可用功能清单

```
✅ bin/vttest：菜单式 VT100/ANSI 兼容性测试（-V 版本、-c 回放、-l 记录、-p/-q/-s/-u/-8 选项）
✅ share/man/man1/vttest.1：man page 随包安装
✅ test_package：CLI 断言 6 条 + PTY 交互断言 3 条，全部在 OHOS 目标上实跑
```

### 2.4 已知限制

1. L2 通用冒烟脚本按 `--version/--help` 探测，而 vttest 上游接口为 `-V`；该项
   在本地与平台 CI 中记录为 skip（脚本内明确非阻塞），不作为缺陷处理。
2. PTY 交互断言需要宿主提供 `/dev/ptmx`；无伪终端的宿主会显式 SKIP（exit 77），
   不伪装通过。HarmonyOS PC 真机上实测执行。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| `test -x <pkg>/bin/vttest` | 包内可执行文件存在 | ✅ PASS |
| `vttest -V \| grep -Fx "VT100 test program, version 2.7 (20251205)"` | 版本横幅与上游一致 | ✅ PASS |
| `vttest -V > /dev/null` | 版本查询退出码 0 | ✅ PASS |
| `vttest -Z 2>&1 \| grep -F "Usage: vttest"` | 未知选项输出用法文本 | ✅ PASS |
| `! vttest -Z > /dev/null 2>&1` | 未知选项非零退出（负向对照） | ✅ PASS |
| `test -s <pkg>/share/man/man1/vttest.1` | man page 安装且非空 | ✅ PASS |
| `pty_smoke.py`：版本横幅出现在 PTY 输出 | 真实终端下的启动输出 | ✅ PASS |
| `pty_smoke.py`：主菜单 `Choose test type:` 出现 | 菜单驱动界面可用 | ✅ PASS |
| `pty_smoke.py`：选择 Exit 菜单项后退出码 0 | 交互闭环干净退出 | ✅ PASS |

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| 无 | — | — |

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| 无（PTY 测试在 OHOS 真机实际执行，未跳过） | — |

---

## 四、关键问题分析

### 问题1: configure 无法识别 HarmonyOS（cannot guess build type）

**现象**：
```
config.guess: unable to guess system type
...
uname -s = HarmonyOS
configure: error: cannot guess build type; you must specify one
```

**根因分析**：
上游 config.guess（GNU 2025-07-10）的 `case $UNAME_SYSTEM` 只识别 `Linux|GNU|GNU/*`；
HarmonyOS PC 的 `uname -s` 返回 `HarmonyOS`。此外 config.guess 的
`set_cc_for_build()` 用 `umask 077` 建编译器探测目录，在 HMDFS 上得到
`drwx--S---`（setgid 强制），owner 也无法写入，探测编译失败。

**解决方案**：
`patches/0001-config.guess.patch` 为 `UNAME_SYSTEM` 情况加入 `HarmonyOS`、
新增 `aarch64:HarmonyOS:*:*` → `aarch64-unknown-linux-$LIBC` 分支，并把三处
`umask 077` 改为 `umask 022`。原生构建无需 `--host` 即可识别自身
（知识库 E160 / E011）。

### 问题2: config.status 临时目录不可写（could not setup config files machinery）

**现象**（未打补丁的 configure 实测，为绕开 config.guess 显式传 `--build/--host`）：
```
./config.status: line 737: .../tmp-a/csLPcIOn/undefs.sed: Permission denied
./config.status: line 753: .../tmp-a/csLPcIOn/out: Permission denied
./config.status: line 763: .../tmp-a/csLPcIOn/config.h: Permission denied
（共 21 处 Permission denied；config.h 未生成）
$ make -j1
make: *** No rule to make target '.1', needed by '.txt'.  Stop.
```
打补丁后同一命令：0 处 Permission denied、config.h（3140 字节）正常生成、make rc=0、
`./vttest -V` 输出正确版本横幅。

**根因分析**：
autoconf 生成的 config.status 内联脚本用
`(umask 077 && mktemp -d "$TMPDIR/csXXXXXX")` 建临时目录；HMDFS 对 umask 077
新建目录强制 setgid，权限归一化为 `drwx--S---`，owner 无法写入其中文件
（知识库 E129/E112/E136）。

**解决方案**：
`patches/0002-configure.patch` 把 configure 内两处 `umask 077` 改为 `umask 022`
（与已合入的 a52dec/0.7.4、teseq/1.1.1 同款修复）。

---

## 五、测试环境

```
vttest 2.7 (20251205) / Conan 包版本 2.7-20251205
源: https://invisible-island.net/archives/vttest/vttest-20251205.tgz
    sha256 cd6886f9aefe6a3f6c566fa61271a55710901a71849c630bf5376aa984bf77cc
补丁: 0001-config.guess.patch, 0002-configure.patch
构建: autotools; ./configure && make; make install DESTDIR=<package_folder>
编译器: clang 15.0.4 (OHOS SDK 26.0.0.18); profile ohos-aarch64-device
验证: conan-verify G0–G4 PASS；clean-verify G0 干净构建复现通过（tarball+2 补丁→configure→make→make install）；
      本地 CI L0/L1/L1e/L4/L5 pass；test_package 9/9 PASS
```

---

*报告生成时间: 2026-09-21*
