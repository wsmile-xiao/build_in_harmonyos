# rocminfo 6.4.3 适配笔记（OpenHarmony PC）

## 编译环境
- 构建系统: script-only（交付件为纯 Python 组件，无编译步骤）
- 编译日期: 2026-10-04
- 编译器: clang/clang++ 15（OpenHarmony SDK `aarch64-unknown-linux-ohos-clang`）
- 目标: OpenHarmony 6.0.0.47 / API20 / aarch64
- 状态: built

## 软件说明
`rocminfo` 是 ROCm 的系统信息工具，上游 `rocm-6.4.3` 标签的仓库**只有 18 个文件**、
两个交付件：

| 交付件 | 上游构建方式 | 在 OHOS PC 上 |
|---|---|---|
| `rocminfo`（CLI） | CMake + `find_package(hsa-runtime64 1.0 REQUIRED)` | **不可用**（见下） |
| `rocm_agent_enumerator` | 上游仅 `configure_file(... COPYONLY)`，纯 Python 脚本 | **可用**（本配方交付） |

## 为什么只交付 `rocm_agent_enumerator`

`rocminfo` CLI 的全部功能是调用 HSA 运行时枚举 AMD GPU agent。它在 OHOS PC 上有
两个**互相独立**的致命阻塞：

1. **构建期**：`CMakeLists.txt:63` 硬性 `find_package(hsa-runtime64 1.0 REQUIRED)`；
   制品仓检索 `hsa*`/`hsakmt*`/`kfd*` 全部 0 命中，sysroot 亦无。
2. **运行期**：其下层 `libhsakmt` 硬编码 `open("/dev/kfd")`
   （`ROCR-Runtime/libhsakmt/src/openclose.c:47`），`/dev/kfd` 由内核 `amdkfd`
   创建 —— OHOS PC 无该驱动、无 AMD GPU。

**为什么不给 CLI 打个 stub 硬编过去**：实测过。用真实 HSA 头 + 诚实最小 HSA 实现，
`rocminfo` 可以交叉编译并链接成 OHOS aarch64 静态 ELF，但运行行为是
**枚举 0 个 agent、任何参数都 exit 8** —— 即一个"名称在、功能无"的空壳。
按仓库规则"不得裁剪软件"，交付这种产物不可接受，故不构建 CLI。

**为什么交付 `rocm_agent_enumerator` 不是裁剪**：上游 README 明确记载它有
**五种** ISA 生成方式，其中方式 1、2 存在的理由就是"没有 ROCm 栈"的场景
（原文：*"This can be used in an install environment with sandbox, where execution
of rocminfo is not possible"* / *"This is used in a container setting where ROCm
stack may usually not available"*）：

| # | 方式 | 依赖 | OHOS PC |
|---|---|---|---|
| 1 | `ROCM_TARGET_LST` 环境变量指向 target.lst | **无** | ✅ |
| 2 | 与脚本同目录的 `target.lst` | **无** | ✅ |
| 3 | HSA topology `/sys/class/kfd/...` | KFD | ❌ |
| 4 | `lspci` + 内置查表 | lspci | ❌ |
| 5 | `rocminfo` 二进制 | 完整 ROCm 栈 | ❌ |

方式 1/2 的函数契约（读文件 → 逐行输出 GCN ISA 名 → exit 0）在 OHOS PC 上**完整可用**。
这是上游文档化的 sandbox/container 用法，与 OHOS PC 的环境同构，
交付的是真实功能，不是空壳。

## 包内容
- `bin/rocm_agent_enumerator` — 上游原版脚本，未做任何修改
- `docs/README.md` — 上游 README
- `docs/*.rst` — 上游 `docs/` 参考文档
- `docs/OHOS-NOTES.md` — 本平台部署说明（含可用/不可用路径清单）
- `licenses/License.txt` — 上游 NCSA 许可证

## 消费者使用说明
- 交付件是 Python 脚本，**需要消费者提供 `python3`**。OHOS PC 镜像默认不带
  Python 解释器；这是环境事实，已写入 `docs/OHOS-NOTES.md`。
- 两种可用用法：

  ```sh
  # 方式 1：环境变量
  ROCM_TARGET_LST=/path/to/target.lst python3 rocm_agent_enumerator

  # 方式 2：同目录 target.lst
  cp target.lst "$(dirname "$(command -v rocm_agent_enumerator)")"
  python3 rocm_agent_enumerator
  ```

- `target.lst` 每行一个 GCN 目标名；`#` 开头的行与空行被忽略（上游 `getGCNISA`
  用 `match` 从行首匹配，故注释行天然被跳过）。

## 上游测试清点（R51）
- 上游 `CMakeLists.txt` **无** `enable_testing()` / `add_test`，全树 **无**测试目录。
- 上游 CI（`.github/workflows/rocm_ci_caller.yml`、`.azuredevops/rocm-ci.yml`）
  仅做构建，**不跑测试**。
- 结论：上游测试用例数 **N = 0**。

## 新增测试（本配方 `test_package/`）
上游 N=0，按规则补增**鸿蒙特有消费者用例**。测试入口遵循仓库
`templates/test_package-executable/` 的形态：`conanfile.py` 的 `test()` 在
`conanrun` 环境下驱动 `test.sh`，真实断言全部落在 `test.sh` 里。

| # | 用例 | 验证内容 |
|---|---|---|
| 1 | 交付件完整性 + 可执行位 + 解释器可用 | `bin/rocm_agent_enumerator` 在 PATH 上、是常规文件、有可执行位与 shebang；宿主必须有 `python3`/`python`（缺失即失败，不静默通过） |
| 2 | E2E 方式 2（同目录 `target.lst`） | 以**已安装命令**方式执行，stdout 精确等于 `gfx906/gfx908/gfx1030`，退出码 0；注释行与空行按上游契约被忽略 |
| 3 | E2E 方式 1（`ROCM_TARGET_LST`） | 同上，stdout 精确等于 `gfx90a/gfx942`，退出码 0 |
| 4 | 文档化优先级 | `ROCM_TARGET_LST` 必须胜过同目录 `target.lst` |
| 5 | 负对照 | 无任何目标来源时**不得**凭空输出目标（防"总是打印固定内容"的假实现） |

共 **5 组用例 / 9 个断言点**。

### 为什么改掉旧的 `python3 <脚本路径>` 调用方式（AI 检视意见的实质处理）
AI 检视指出：旧实现用 `"<py>" ./rocm_agent_enumerator` 驱动被测件，此时**真正被测的是
宿主解释器**，一个"没交付任何可用命令"的包同样会通过 —— 该指摘成立，已改正。

现在的调用方式对齐上游的消费者契约：

- 上游 `CMakeLists.txt:180` → `install(PROGRAMS ... DESTINATION ${CMAKE_INSTALL_BINDIR})`，
  即 `rocm_agent_enumerator` 是被**安装成命令**的；
- 上游 README Execution 一节也把它与 `rocminfo` 并列为 build folder 里的可执行程序；
- 因此测试用 `command -v rocm_agent_enumerator` 在 PATH 上定位**包安装出来的那个文件**
  （由本包 `package_info` 的 `runenv_info` 前置进 PATH），再直接执行它
  （脚本自带 `#!/usr/bin/env python3`）。包若没装出这个命令，`command -v` 找不到
  ⇒ 用例 1 直接失败，这正是 R34 / L1e 要保证的"产物移动后测试必红"。

实测：`conan create` → **exit 0**，**5/5 用例通过**（日志见 PR 描述与
`verification_report.md`）。执行后工作副本**无残留**（`mktemp -d` + `trap` 清理，
临时目录不在源码树内）。

### 静态门禁核验（ELF64 AArch64）
交付件是**解释型 Python 脚本**（`file` 判定 `Python script, ASCII text executable`），
`readelf` 无法对其报告 machine/class。为避免把"构建成功"当成"ELF 正确"，
另用**真实 OHOS 6.0 aarch64 工具链**做了一次静态链接编译核验，过程记录在
`verification_report.md`：

```console
$ $SDK/native/llvm/bin/aarch64-unknown-linux-ohos-clang++ -target aarch64-linux-ohos \
      --sysroot=$SDK/native/sysroot --rtlib=compiler-rt -static -O2 gate_probe.cpp -o gate_probe
COMPILE_EXIT=0
$ readelf -h gate_probe
  Class:   ELF64
  Machine: AArch64
$ readelf -d gate_probe | grep NEEDED     -> (无)   => 静态链接
```

该探针同时 `#include` 了 `linux/kfd_ioctl.h` 与 `drm/amdgpu_drm.h`（见上方反例说明），
即"缺少 KFD/AMDGPU UAPI 头"确实**不是**本任务的阻塞理由。

## 验证结果
- `conan create archives/r/rocminfo/6.4.3 --profile:host=ohos-aarch64-run --profile:build=ohos-aarch64-run`
  → **exit 0**（清空 `rocminfo/*` 缓存后复验；日志 6,874 bytes）
- `test_package` → **5/5 通过**、9 个断言点，日志内 `error/failed/traceback` 命中 **0**
- 静态门禁 → `file` / `readelf -h` 实测 **ELF 64-bit LSB executable, ARM aarch64**，静态链接
- 真机（DAYU200-RK3568 / OpenHarmony 6.0.0.47 / aarch64）→ 见 PR 描述与
  `_device_evidence.json`

## 已知限制
- `rocminfo` CLI 不交付（结构性不可适配，判定详见
  `knowledge/drafts/DRAFT-rocminfo-6.4.3-kernel-device-node-gated-userspace-runtime.md`）。
- 交付件为 Python 脚本，设备需自带解释器；无解释器时脚本无法执行（不是本配方的缺陷）。
