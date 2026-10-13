# rocminfo 6.4.3 · 验证报告（OpenHarmony PC）

> 本文件是本轮针对人工评审意见所做的**可复现验证记录**，随 `archives/r/rocminfo/6.4.3/` 交付。
> 所有数字均取自真实运行日志与文件哈希，**无估算、无占位符**。
>
> | 项 | 值 |
> |---|---|
> | PR head（本报告对应的提交前状态） | `a96de2d298d75672209018871745bbb23b3c6a9f` |
> | 平台任务 | `10212`（`rocminfo` 6.4.3，`taskBranch = feat/rocminfo-6.4.3`） |
> | 上游 tag | `rocm-6.4.3` |
> | 验证宿主 | WSL2 Ubuntu 22.04（无 AMD GPU）+ OHOS 6.0 SDK |
> | 目标平台 | OpenHarmony 6.0.0.47 / API20 / aarch64 |
> | 报告日期 | 2026-10-08 |

---

## 1. `conan create` 实测（本轮清缓存复验）

```console
$ conan remove 'rocminfo/*' -c
$ conan create archives/r/rocminfo/6.4.3 \
      --profile:host=ohos-aarch64-run --profile:build=ohos-aarch64-run
...
rocminfo/6.4.3: package(): Packaged 1 '.txt' file: License.txt
rocminfo/6.4.3: package(): Packaged 5 '.rst' files
rocminfo/6.4.3: package(): Packaged 2 '.md' files: OHOS-NOTES.md, README.md
rocminfo/6.4.3: package(): Packaged 1 file: rocm_agent_enumerator
...
======== Testing the package ========
======== Testing the package: Executing test ========
rocminfo/6.4.3 (test package): rocminfo consumer e2e driver: /data/service/hnp/bin/bash test.sh
rocminfo/6.4.3 (test package): RUN: /data/service/hnp/bin/bash test.sh
--- rocminfo 6.4.3 consumer e2e ---
consumer command: /root/.conan2/p/b/rocmi39397fa7a6ff4/p/bin/rocm_agent_enumerator
PASS 1: package artifact present and executable (/root/.conan2/p/b/rocmi39397fa7a6ff4/p/bin/rocm_agent_enumerator), interpreter /root/ohpc/venv/bin/python3
PASS 2: strategy 2 (colocated target.lst, comments/blanks parsed) -> gfx906 gfx908 gfx1030
PASS 3: strategy 1 (ROCM_TARGET_LST env var) -> gfx90a gfx942
PASS 4: documented precedence (env var beats colocated file) -> gfx90a gfx942
PASS 5: negative control (no target source -> no invented target)
test rocminfo 6.4.3: 5/5 consumer checks PASS

CONAN_EXIT=0
```

| 复验项 | 实测值 |
|---|---|
| `conan create` 退出码 | **0** |
| 日志文件 | `/root/roc_verify_r27.log`，**6,874 bytes** / 139 行 |
| 日志内 `PASS` 行数 | **6**（5 个用例 + 1 行汇总） |
| 日志内 `error`/`failed`/`traceback` 命中 | **0** |
| `test_package` 用例 | **5/5 通过**（9 个断言点） |
| 执行后工作副本残留 | **无**（`git status --porcelain` 只显示本轮 3 个待提交文件） |
| 中间文件落点 | `mktemp -d` 生成的临时目录，`trap` 退出即清理，**不在源码树内** |

### 交付件哈希（上游原版脚本，逐字节未改）

```console
$ sha256sum rocm_agent_enumerator
3adbb8fb487d05668eb44069e692832c8e4b7c81315c523a9a18a0a84485cba6  rocm_agent_enumerator
$ stat -c '%s bytes' rocm_agent_enumerator
9980 bytes
$ file rocm_agent_enumerator
Python script, ASCII text executable
```

### 上游源码归档

```console
$ sha256sum /root/work/dl/rocminfo-rocm-6.4.3.tar.gz
0aa040963daaa2b5ebbec818a2d53c83612912686336160c223fb664dc0ca92b  rocminfo-rocm-6.4.3.tar.gz
```

---

## 2. 消费者测试用例明细（`test_package/test.sh`）

| # | 用例 | 断言内容 | 实测结果 |
|---|---|---|---|
| 1 | 交付件完整性 + 可执行位 + 解释器 | `command -v rocm_agent_enumerator` 命中；是常规文件；有可执行位；有 shebang；宿主有 `python3`/`python` | PASS |
| 2 | 方式 2 — 脚本同目录 `target.lst` | stdout 精确等于 `gfx906/gfx908/gfx1030`；退出码 0；`#` 注释行与空行被忽略 | PASS |
| 3 | 方式 1 — `ROCM_TARGET_LST` | stdout 精确等于 `gfx90a/gfx942`；退出码 0 | PASS |
| 4 | 文档化优先级 | `ROCM_TARGET_LST` 胜过同目录 `target.lst`（后者写 `gfx900`，输出仍为 `gfx90a/gfx942`） | PASS |
| 5 | 负对照 | 无任何目标来源时 stdout 为空（不得凭空输出） | PASS |

### 2.1 被测对象是"包安装出来的命令"，不是宿主解释器

调用链：`package_info()` 的 `runenv_info.prepend_path("PATH", <pkg>/bin)`
→ 测试在 `conanrun` 环境下 `command -v rocm_agent_enumerator`
→ 得到 `/root/.conan2/p/b/rocmi39397fa7a6ff4/p/bin/rocm_agent_enumerator`
→ **直接执行该文件**（脚本自带 `#!/usr/bin/env python3`）。

这与上游的交付契约一致：

- `CMakeLists.txt:180` → `install(PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/rocm_agent_enumerator DESTINATION ${CMAKE_INSTALL_BINDIR})`
- 上游 README「Execution」把 `rocm_agent_enumerator` 与 `rocminfo` 并列为
  「will be in the build folder」的可执行程序。

⇒ 包若没有安装出这个命令，用例 1 会立即失败（`R34` / `L1e` 所要求的
"产物移走后测试必红"由此成立）。

---

## 3. 静态产物核验（ELF64 AArch64）

**诚实说明**：本包交付的 `rocm_agent_enumerator` 是**解释型 Python 脚本**
（`file` 判定 `Python script, ASCII text executable`），
**`readelf` 对它无 machine/class 可报**。因此"产物是 ELF64 AArch64"这一条
不能、也不应挂在交付件自身上。

为避免把"构建成功"当作"ELF 正确"，另用**真实 OHOS 6.0 aarch64 工具链**
做了一次静态链接编译核验：

```console
$ /root/ohpc/sdk/ohos-6.0/native/llvm/bin/aarch64-unknown-linux-ohos-clang++ \
    -target aarch64-linux-ohos \
    --sysroot=/root/ohpc/sdk/ohos-6.0/native/sysroot \
    --rtlib=compiler-rt -static -O2 gate_probe.cpp -o gate_probe
COMPILE_EXIT=0

$ file gate_probe
ELF 64-bit LSB executable, ARM aarch64, version 1 (SYSV), statically linked, with debug_info, not stripped

$ readelf -h gate_probe
  Class:                             ELF64
  Data:                              2's complement, little endian
  Type:                              EXEC (Executable file)
  Machine:                           AArch64

$ readelf -d gate_probe | grep NEEDED
  (无输出)                          ⇒ 静态链接，无运行时 .so 依赖

$ sha256sum gate_probe
  8596cba200de29241bf16c0ba4903f7f43a9f0fa478b58555bb6d1880066472b  gate_probe
$ stat -c '%s bytes' gate_probe
  817608 bytes
```

`gate_probe.cpp` 同时 `#include <linux/kfd_ioctl.h>` 与 `<drm/amdgpu_drm.h>`，
编译通过 —— 这**再次证伪**"鸿蒙缺 KFD/AMDGPU UAPI 头"这条论据（见 `notes.md` 反例说明）。

工具链版本（`--version` 首行）：clang version 15.0.4，target `aarch64-unknown-linux-ohos`。

---

## 4. 真机（OpenHarmony PC · DAYU200-RK3568）

### 4.1 截至本报告：设备排队中（如实说明，不冒充已跑）

```console
$ bash automation/device_runner.sh check
DEVICE:READY serial=450100445634303332018f3e7d2dba00
OpenHarmony 6.0.0.47

$ bash automation/device_runner.sh run roc_probe_r27 /root/work/x/roc/rocminfo-rocm-6.4.3 "sh .../_roc_devprobe.sh"
[device_runner] 设备忙，未获授予：{"granted": false, "timeout": true, "position": 5, "eta_s": 69722}
```

设备物理在线（`DEVICE:READY`），但**单台设备**被其它任务以 FIFO 租约占用；
本任务当时排在**第 5 位**，resbroker 给出的预计等待 `eta_s = 69722`（≈19.4 小时）。
本轮的设备请求已在队内（holder 名 `roc_probe_r27`），一旦获授即执行 §4.3 的核验。

### 4.2 已有的真机证据（2026-10-05，设备 job `rocminfo_e2e`）

```console
$ sh probe.sh            # 设备侧
date  : Fri Aug  4 21:03:00 CST 2017
uname : Linux localhost 6.6.101 #1 SMP Mon Sep 28 19:29:42 CST 2026 aarch64
sw    : OpenHarmony 6.0.0.47
dir   : /data/local/tmp/ohpc_test/rocminfo_e2e

PYTHON: NOT_FOUND
PYTHON_ABSENT: 设备无 python 解释器 —— 这是 OHOS PC 的既知事实

---- A. rocminfo CLI 运行期阻塞核验 ----
A_kfd      = ABSENT
B_topology : ls: /sys/class/kfd/kfd/topology/nodes: No such file or directory
B_amdkfd   : ls: /sys/module/amdkfd: No such file or directory
C_hsa_libs : 0
C_inc_hsa  : ls: /usr/include/hsa: No such file or directory
D_amd_gpu  : 0

---- F/G. 反例核对 ----
F_absent : /usr/include/linux/kfd_ioctl.h
F_absent : /usr/include/drm/amdgpu_drm.h
G_dev_dri  : card0
             renderD128

__RC__=0
```

**这条证据同时给出了一个必须如实说明的限制**：目标镜像**没有 Python 解释器**，
所以作为 Python 脚本形态交付的 `rocm_agent_enumerator` **在本设备上无法被执行**，
§2 的 5 项用例目前**只在宿主/CI（x86_64 + python3）上实跑通过**，
**尚未在真机上产生用例通过记录**。这是环境事实（已写入
`docs/OHOS-NOTES.md`），不是配方的通过声明。

### 4.3 设备获授后要跑的核验（命令已备好，待排队）

```sh
# 逐条尝试设备上可能存在的解释器，并把结论落盘
for c in python3 python python3.11; do command -v "$c"; done
ls /data/service/hnp/bin 2>/dev/null | head
# 若存在任一解释器：以消费者方式执行交付件并校验 stdout/退出码
# 若全部 NOT_FOUND：记录 INTERPRETER_ABSENT，明确标注"用例无法在真机执行"
```

结论会**原样回填**本报告与 PR 描述，不做任何美化。

---

## 5. 上游测试清点（R51 三步法）

```console
$ grep -rn 'enable_testing\|add_test' rocminfo-rocm-6.4.3/ --include='*.txt' --include='*.cmake' | wc -l
0
$ ls -d rocminfo-rocm-6.4.3/tests
ls: cannot access 'rocminfo-rocm-6.4.3/tests': No such file or directory
$ ls rocminfo-rocm-6.4.3/.azuredevops
rocm-ci.yml
$ ls rocminfo-rocm-6.4.3/.github/workflows
rocm_ci_caller.yml
```

| 项 | 实测 |
|---|---|
| `enable_testing()` / `add_test()` | **0 处** |
| `tests/` 目录 | **不存在** |
| 上游 CI（GitHub Actions + Azure Pipelines） | 仅构建，**不跑测试** |

⇒ 上游测试用例数 **N = 0**，`conanfile.py` 的 `build()` 中无可集成的 `make check`。
`test_package/MANIFEST.yml` 已按此填写（`upstream_tests: []`）。

---

## 6. 本报告涉及文件的哈希（便于复核）

| 文件 | sha256 |
|---|---|
| `conanfile.py` | `c99a86f95246fae4a9c4c7c176a983965569111fa8db435d13a8e5e9badc90ba` |
| `conandata.yml` | `277f5d4059ecee6772a3963350001579239c793be6e17ef4fd10932aa2b8dc0b` |
| `manifest.yaml` | `c633b940999ed7f022108d5e11468f9b1b6cbe4430690c6f9d3d4d1187652e36` |
| `notes.md` | `1cfab5b26885bdedfaee6701c7745f168181051e1d5d068172739cf4aa244ebc` |
| `test_package/conanfile.py` | `72d56ce80712fdf03af24bbad0e1c6f8f435cf3331d52c56e384034b28332eab` |
| `test_package/test.sh` | `fe4753a4a345eaa7a99bb7ff75f8076226e5ca67cf2347b4cb2e701d42f97c71` |
| `test_package/MANIFEST.yml` | `dd20af013e8746deb05ee41e62f50a46f6bb5bcfb983309f5d7b6491b12e365f` |
| 交付件 `rocm_agent_enumerator`（上游原版） | `3adbb8fb487d05668eb44069e692832c8e4b7c81315c523a9a18a0a84485cba6` |
| 上游源码归档 `rocm-6.4.3.tar.gz` | `0aa040963daaa2b5ebbec818a2d53c83612912686336160c223fb664dc0ca92b` |
| 静态门禁探针 `gate_probe` | `8596cba200de29241bf16c0ba4903f7f43a9f0fa478b58555bb6d1880066472b` |

---

## 7. 已知限制（不做任何粉饰）

1. **`rocminfo` CLI 不交付**：结构性不可适配（构建期 `find_package(hsa-runtime64 1.0 REQUIRED)`
   零命中 + 运行期 `libhsakmt` 硬编码 `/dev/kfd`，平台无 `amdkfd` 与 AMD GPU）。
   完整判定见 `knowledge/drafts/DRAFT-rocminfo-6.4.3-kernel-device-node-gated-userspace-runtime.{kv,md}`
   与【无法适配】issue [#3625](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3625)。
2. **交付件需要消费者提供 Python 解释器**：OHOS PC 默认镜像无 `python3`
   （真机实测 `PYTHON: NOT_FOUND`）。这是环境事实，已写入 `docs/OHOS-NOTES.md`
   与 `test_package/MANIFEST.yml`。
3. **真机用例尚未产出**：设备排队中（见 §4.1）。在拿到真机结果前，
   本报告**不声称**任何真机用例通过数。
