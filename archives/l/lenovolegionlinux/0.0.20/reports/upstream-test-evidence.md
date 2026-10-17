# lenovolegionlinux 0.0.20 — 上游测试逐条实测证据

本文件记录 PR 描述中「上游 12 个用例：执行 2 / 阻塞 10」的逐条原始证据。
所有数字与输出均为实测，未执行的一律标注为未执行（不声明通过）。

## 0. 环境

| 项 | 值 |
|---|---|
| 目标 | aarch64-unknown-linux-ohos（OpenHarmony PC） |
| OHOS SDK / sysroot | `ohos-sdk_26.0.0.18/ohos/native/sysroot` |
| 交叉 clang | `/data/service/hnp/bin/clang`（Ubuntu clang 15.0.7，target aarch64-unknown-linux-ohos） |
| 适配后 python | 随 conan 运行的解释器（CI 侧即 OHOS/HNP Python），PyYAML 由依赖 `pyyaml/6.0.2` 提供 |
| 上游源码 | tag `v0.0.20`，sha256 `c9974cfde03d8fd73de0a09628189f8fd9341037f10e28649b2fe5d1ec68bb2e` |

## 1. 上游用例总数口径（实测）

```text
$ ls tests/*.sh | wc -l
12
```

上游**没有** `make check` / `ctest` / `pytest` 目标（顶层无 Makefile；构建系统是
`kernel_module/Makefile` 的 Kbuild 与 `python/setup.cfg` 的 setuptools），
12 个 shell 脚本即全部用例，逐脚本手工调用。

## 2. 逐条结果

| # | 用例 | 结果 | 证据 |
|---|---|---|---|
| 1 | `test_kernel_build.sh` | 阻塞（未执行） | `make -C /lib/modules/$(uname -r)/build ... modules` → `/lib/modules/.../build: No such file or directory`，`Error 2` |
| 2 | `test_kernel_checkpath.sh` | 阻塞（未执行） | `deploy/dependencies/install_dir/checkpatch.pl: No such file or directory`（上游 submodule 未随 tarball 分发），exit 127 |
| 3 | `test_kernel_dkms_install.sh` | 阻塞（未执行） | 脚本首行 `sudo apt-get install dkms openssl mokutil` + `sudo make dkms`；`command -v dkms` → 无；需 root 与 apt |
| 4 | `test_kernel_install.sh` | 阻塞（未执行） | 首步 `make` 与 #1 同因失败（exit 2）；后段 `sudo make install` 需 root 写 `/lib/modules` |
| 5 | `test_kernel_reload.sh` | 阻塞（未执行） | `sudo make reloadmodule` ×20：需 root + 已加载的内核模块 + 已构建的 `.ko` |
| 6 | `test_python.sh` | 阻塞（未执行） | `pylint ...` → `pylint: command not found`，exit 127（制品仓无 pylint 制品） |
| 7 | **`test_python_cli.sh`** | **执行并通过** | 见 §3.1（对包内上游源码快照逐字执行，exit 0） |
| 8 | **`test_python_cli_installed.sh`** | **执行并通过** | 见 §3.2（对包内 `bin/legion_cli` 逐字执行，exit 0） |
| 9 | `test_python_gui.sh` | 阻塞（未执行） | `xvfb-run ... legion_gui.py --automaticclose` → `xvfb-run: command not found`，exit 127；且 `import PyQt6` 失败 |
| 10 | `test_python_gui_installed.sh` | 阻塞（未执行） | 同上（`xvfb-run: command not found`，exit 127） |
| 11 | `test_python_installed.sh` | 阻塞（未执行） | 组合脚本，内部调用 #8 + #10，随 GUI 用例阻塞 |
| 12 | `test_python_run_gui_root.sh` | 阻塞（未执行） | `sudo pkexec ls`：需 polkit 提权（OHOS 侧无 polkit/pkexec 面）；本仓适配流程运行于非特权用户空间 |

> 「未执行」= 前置条件在 OHOS PC 适配环境内不存在，命令根本无法启动或必然失败。
> 按平台要求「不得跳过测试、不得伪造通过」，这 10 条既不计入通过数，也不伪造原因。

## 3. 两条真实执行的用例

### 3.1 `tests/test_python_cli.sh`（上游源树变体）

上游脚本原文（未改一行，随包交付于
`share/lenovolegionlinux/upstream/tests/test_python_cli.sh`）：

```bash
#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Smoketest CLI
${DIR}/../python/legion_linux/legion_linux/legion_cli.py --donotexpecthwmon
```

实测（`conan create` 的 test 阶段，cwd 为包内快照）：

```text
lenovolegionlinux/0.0.20 (test package): RUN: bash "<pkg>/share/lenovolegionlinux/upstream/tests/test_python_cli.sh"
+ DIR=<pkg>/share/lenovolegionlinux/upstream/tests
+ <pkg>/share/lenovolegionlinux/upstream/tests/../python/legion_linux/legion_linux/legion_cli.py --donotexpecthwmon
usage: legion_cli.py [-h] [--donotexpecthwmon] [--loglevel {...}] {autocomplete-install,...}
...
exit code: 0
```

### 3.2 `tests/test_python_cli_installed.sh`（已安装变体）

上游脚本原文（逐字副本，位于 `test_package/test_python_cli_installed.sh`）：

```bash
#!/bin/bash
set -ex
legion_cli --donotexpecthwmon
echo "Done"
```

实测（`conanrun` 环境把包内 `bin/` 加入 PATH，`legion_cli` 即本包交付的控制台入口）：

```text
lenovolegionlinux/0.0.20 (test package): RUN: bash "<test_package>/test_python_cli_installed.sh"
+ legion_cli --donotexpecthwmon
usage: legion_cli [-h] [--donotexpecthwmon] [--loglevel {...}] {autocomplete-install,...}
...
+ echo Done
Done
exit code: 0
```

## 4. 内核态为什么无法执行（可复现的实测证据）

### 4.1 逐头核验（修正后的抽取命令，`grep -hE ... | sed -E 's/.*<([^>]+)>.*/\1/'`）

```text
16 个头：present=5, missing=11
MISSING  asm/io.h
MISSING  linux/acpi.h
MISSING  linux/debugfs.h
MISSING  linux/delay.h
MISSING  linux/dmi.h
MISSING  linux/hwmon-sysfs.h
MISSING  linux/hwmon.h
present  linux/kernel.h (25 lines)      ← UAPI 桩
present  linux/module.h (23 lines)      ← UAPI 桩
MISSING  linux/leds.h
MISSING  linux/moduleparam.h
MISSING  linux/platform_device.h
MISSING  linux/platform_profile.h
present  linux/types.h (39 lines)       ← UAPI 桩
present  linux/version.h (20 lines)
present  linux/wmi.h (62 lines)         ← UAPI 桩
```

`linux/module.h` 的 UAPI 桩性质（逐符号命中数）：

```text
$ wc -l $SYSROOT/usr/include/linux/module.h
23
$ grep -c MODULE_LICENSE / module_init / module_exit / THIS_MODULE / "struct module" / __init
0 0 0 0 0 0
$ grep -c _UAPI_ $SYSROOT/usr/include/linux/module.h
2
```

### 4.2 无内核构建树

```text
usr/src                                  MISSING
usr/include/linux/kconfig.h              MISSING
usr/include/config                       MISSING
usr/include/generated                    MISSING
```

### 4.3 交叉 clang 实测（失败于第一个内核内部头）

```text
$ /data/service/hnp/bin/clang --target=aarch64-linux-ohos --sysroot=$SYSROOT \
      -I. -fsyntax-only legion-laptop.c
legion-laptop.c:62:10: fatal error: 'linux/acpi.h' file not found
#include <linux/acpi.h>
         ^~~~~~~~~~~~~~
1 error generated.
exit code: 1
```

### 4.4 Kbuild 方式（无 `modules` 目标）

```text
$ bash tests/test_kernel_build.sh
+ cd kernel_module
+ make
make -C /lib/modules/<kver>/build M=<...>/kernel_module modules
make[1]: *** /lib/modules/<kver>/build: No such file or directory.  Stop.
make: *** [Makefile:13: all] Error 2
exit code: 2
```

## 5. 适配侧新增测试的实测结果（`conan create` test 阶段）

```text
[ohos][ ok ] site-packages layout + bin/legion_cli entry point
[ohos][ ok ] packaged legion_linux imports under Python <ver>
[ohos][ ok ] CLI reports the missing kernel interface instead of fabricating features
[ohos][ ok ] no Python traceback (graceful degradation) on the OHOS PC baseline
[ohos][ ok ] argcomplete optional (patch 0001 effective)
[ohos][ ok ] no prebuilt .ko shipped (kernel-state build is not claimed)
[ohos][ ok ] upstream source snapshot shipped (kernel_module/ + tests/ + python/)
[ohos] ALL OHOS PLATFORM CHECKS PASSED

[km][ ok ] module_init() present / module_exit() present / MODULE_LICENSE() present
[km][ ok ] WMI hardware interface used / ACPI hardware interface used
[km][ ok ] DMI vendor allowlist/denylist present
[km][ ok ] hwmon device registration present / platform_profile registration present
[km][ ok ] ACPI EC path identifier present
[km][ ok ] kernel internal includes counted: 16
[km][ ok ] Kbuild obj-m target present / Kbuild KSRC (kernel build tree) required
[km][ ok ] DKMS BUILT_MODULE_NAME declared
[km][ ok ] no prebuilt .ko in the delivered snapshot
[km] kernel module source contract verified (kernel-state build/load NOT claimed)

OK: legion_linux consumer API checks passed (FanCurve YAML round-trip 2 entries,
    facade w/o hwmon, sysfs base path contract)
```

## 6. 仓库 CI 门禁（本地按同一脚本 `ci/conan/build_and_test.sh` 复现）

```text
CI_PACKAGES=archives/l/lenovolegionlinux/0.0.20 \
CI_BRANCH=feat/lenovolegionlinux-0.0.20 zsh ci/conan/build_and_test.sh   → exit 0

G0_RESULT=pass   （知识图谱完整性 540 条）
KC_RESULT=pass   （知识草稿/字段/占位符检查）
JC_RESULT=pass   （运行时状态/二进制/tarball/临时产物/隐藏文件/单软件原子性）
L0_RESULT=pass: all checks passed   （结构、commands.json、依赖已发布、补丁格式、分支名等）
L1_RESULT=pass: test_package executed
  [ok] L1a: test_package was executed by conan create
  [ok] L1b: Test execution evidence found in log
  [ok] L1e: Negative test confirmed — test genuinely depends on lenovolegionlinux
L2_RESULT=pass: legion_cli --help OK, legion_gui failed（GUI 需 PyQt6，见 §2）
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
Build Summary: Total 1 / Success 1 / Pass rate 100.0% (1/1)
```

`L1e`（破坏性反向验证）为本地按 CI 同构逻辑复现：移走包产物 `bin/`、`lib/` 后再跑
`conan test`，测试因找不到 `bin/legion_cli` 与 site-packages 而失败 ⇒ 证明测试真实依赖被测包。

## 7. 明确未声明通过的部分

* 内核模块构建（`.ko`）：无内核构建树 + 缺 11/16 内核内部头，未执行；
* 内核模块加载/卸载与 sysfs/hwmon 读值：需真实 Legion 机型（`DMI_SYS_VENDOR == "LENOVO"`）
  与 root，未执行；
* GUI（`legion_gui`）：需 PyQt6 与 X 服务器，OHOS 侧均不存在，未执行。
