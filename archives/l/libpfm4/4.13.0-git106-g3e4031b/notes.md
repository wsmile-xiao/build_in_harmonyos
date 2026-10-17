# libpfm4 4.13.0-git106-g3e4031b 适配笔记

## 编译环境

- 目标平台：鸿蒙 PC（OHOS）aarch64
- 编译器：OHOS SDK clang（aarch64-unknown-linux-ohos），经 Conan profile 的 `tools.build:compiler_executables` 传入（R33）
- 构建系统：**纯 Makefile**（无 `configure`、无 CMake、无 meson）——`init-build` 生成的 autotools 配方模板不适用，`conanfile.py` 为手写 Makefile 驱动
- Conan profile：`ci/conan/profiles/ohos-aarch64`
- C 标准库：musl（OHOS sysroot）

## 编译步骤

```bash
# 1. 上游快照
#    https://github.com/wcohen/libpfm4
#    commit 3e4031b2ddc555c8178c813925eb5f6872e2daa8（v4.13.0 之后第 106 个提交，故版本号 4.13.0-git106-g3e4031b）

# 2. 构建静态库（最小参数集）
make SYS=Linux ARCH=aarch64 NOPYTHON=y CONFIG_PFMLIB_SHARED=n -j$(nproc) lib

# 3. 上游测试套件（原样编译执行）
make -C tests SYS=Linux ARCH=aarch64 NOPYTHON=y
./tests/validate

# 4. 配方验证 / 本地 CI 模拟
conan create . -pr:a ci/conan/profiles/ohos-aarch64   # build() 内自动执行上游测试套件
```

| 参数 | 作用 |
|------|------|
| `SYS=Linux` | `config.mk` 的 `SYS := $(shell uname -s)` 在鸿蒙返回 `HarmonyOS`，而 `lib/Makefile` 用 `ifeq ($(SYS),Linux)` 守卫 perf_events PMU 的三个源文件；不覆盖 → 编译成功但通用事件整块缺失（静默失败） |
| `ARCH=aarch64` | 选中 `config.mk` 的 `CONFIG_PFMLIB_ARCH_ARM64=y`，启用 ARMv8 PMU 事件表与架构专项测试 |
| `NOPYTHON=y` | 跳过 `python/`（SWIG 绑定子工程），构建机无 SWIG |
| `CONFIG_PFMLIB_SHARED=n` | 静态库（默认），避免与系统同名库冲突（R26） |

## 遇到的问题与解决方案

### 1. 公共头 ABI 常量退化为 32 位（知识 E580）

上游 `include/perfmon/pfmlib.h` / `pfmlib_perf_event.h` 用 `#if __WORDSIZE == 64` 选择 ABI 常量。
`__WORDSIZE` 仅由 glibc 的 `<bits/wordsize.h>` 提供，musl 系 OHOS sysroot 没有该头 → 宏未定义 →
常量取 32 位值，而结构体仍按 LP64 填充 → 公共头契约与真实布局不一致。
上游 `tests/validate` 因此报 5 个 `ABI size` 错误（`pfm_pmu_info_t` / `pfm_event_info_t` /
`pfm_event_attr_info_t` / `pfm_perf_encode_arg_t`）。

**方案**：改用编译器内置 LP64 宏判定
（`defined(__LP64__) || defined(_LP64) || (defined(__SIZEOF_POINTER__) && __SIZEOF_POINTER__ == 8)`），
两个公共头同时修正，库与消费者视图一致。补丁**不含平台宏**，具备上游化条件。
（备选 `-D__WORDSIZE=64` 实测不可行：只能修库自身，消费者包含公共头时仍按 32 位常量编译。）

### 2. perf_events PMU 源文件被静默漏编（知识 E581）

构建零报错、零告警，但 `PERF_COUNT_HW_CPU_CYCLES` 等通用事件查不到；
`make -n lib | grep pfmlib_perf_event` 无输出。原因是 `uname -s` 在鸿蒙返回 `HarmonyOS`，
`lib/Makefile` 的 `ifeq ($(SYS),Linux)` 守卫不成立，`pfmlib_perf_event.c` / `_pmu.c` / `_raw.c`
被跳过。

**方案**：构建期显式传 `SYS=Linux`（不改源码、不新增平台宏），并在 `conanfile.py build()` 内执行
上游测试套件，使这类静默缺陷无法再逃过 CI。

### 3. perf_event 编码在 OHOS 返回 `not supported`

通用 perf PMU 的 `PFMLIB_ENCODE_PERF` 路径返回 `not supported`；上游自带示例 `evt2raw`
在同样输入下同样如此 → 属本环境固有行为（仅通用 perf PMU，无 ARM 专属 perf 编码），
**非缺陷**。测试断言据此校准，不把该行为判为失败。

### 4. `perf_examples` 未纳入构建

OHOS sysroot 的 `sys/poll.h`（musl）重定向在 `-Werror` 下会拦 `task_attach_timeout.c`。
上游测试程序 `validate` 不受影响，故只跳过示例目录（不影响库交付）。

## 源码修改

仅 2 个公共头文件，均为可移植 LP64 判定修复，**不含任何平台宏**（`patch_classification: platform_only=false / guard=none`）：

- `include/perfmon/pfmlib.h`
- `include/perfmon/pfmlib_perf_event.h`

`tests/` 下的上游测试源码**未做任何修改**。

## 依赖版本

- 无第三方库依赖；仅依赖 OHOS sysroot（musl）与内核 `perf_event` 接口
- `python/` SWIG 绑定子工程以 `NOPYTHON=y` 关闭，不引入 SWIG/Python 依赖

## 验证结果

- 上游测试套件 `tests/validate`：`85 × Passed`、`0 × Failed`、末行 `All tests passed`（rc=0）
- `test_package`：`test`（公共 API 9 项）、`test_upstream_validate`（上游表校验 80 项）、`test_ohos`（鸿蒙专项 9 项）全部通过
- 配方验证：`conan create` 干净构建通过（G2/G3/G4）；W3 本地 CI 模拟通过（`.ci-result.json` exit_code=0，含日志 SHA256）
- 详见 `reports/test-report.md`

## 交付物

| 产物 | 路径 | 大小 |
|------|------|------|
| 静态库 | `lib/libpfm.a` | 1,511,264 B |
| 公共头 | `include/perfmon/{pfmlib.h,pfmlib_perf_event.h,perf_event.h,err.h}` | 4 个文件 |
| 许可证 | `licenses/COPYING` | - |

## 发现与知识

- ✅ musl 系 sysroot（OHOS）无 `<bits/wordsize.h>`：以 glibc 专属 `__WORDSIZE` 判断字长的公共头会把 ABI 常量退回 32 位，而结构体仍是 64 位；改用 `__LP64__`/`_LP64`/`__SIZEOF_POINTER__` 可移植判定即可同时修好库与消费者（归档 E580）
- ✅ `SYS := $(shell uname -s)` 在鸿蒙返回 `HarmonyOS`，`ifeq ($(SYS),Linux)` 守卫会静默漏编只在 Linux 下编译的源文件（libpfm4 的 perf_events PMU 三文件）——构建成功、零报错、功能整块缺失，只有跑上游测试才能发现（归档 E581）
- ✅ 纯 Makefile 工程适配：`init-build` 的 autotools 配方模板不适用，需手写 `make` 驱动配方；上游测试套件若始终链接静态库，可直接在 `build()` 内执行，把"上游测试必须全绿"变成 CI 门禁（归档 E581）
- ✅ perf_event 编码对通用 perf PMU 返回 `not supported` 时，先对照上游自带示例（`evt2raw`）确认是否环境固有，再决定测试断言，避免把环境差异误判为适配缺陷（归档 E580/E581 同源经验）

## 对话记录

- 任务指令（人类 → AI）：适配 `libpfm4` 版本 `4.13.0-git106-g3e4031b`；分支名必须为 `feat/libpfm4-4.13.0-git106-g3e4031b`；PR 按模板填写且不得少报测试用例；上游测试用例要全部执行，并至少新增一个鸿蒙特有测试；使用独立 worktree 避免影响其他适配任务；PR 只提交 `archives/`（有价值时一并提交 `knowledge/`）下的文件。
- 关键决策：
  1. ABI 问题采用**可移植 LP64 补丁**而非 `-D__WORDSIZE=64` 或 `__OHOS__` 平台宏（既修库又保证消费者一致，且可上游化）；
  2. `SYS=Linux` 用构建参数覆盖而非修改 Makefile（零源码侵入）；
  3. 上游测试套件搬进 `conanfile.py build()`，把上游测试变成构建门禁；
  4. 交付静态库（R26），`shared` 选项保留在配方中（`CONFIG_PFMLIB_SHARED` 双路径均已实现）。
- 未解决/待跟进：`perf_examples` 因 musl `sys/poll.h` + `-Werror` 未纳入构建（不影响库与上游测试）。
- 工具反馈：`init-build` 对纯 Makefile 工程误判为 autotools 并生成 autotools 配方，需人工改写；`test_package` 生成模板把 CMake 目标命名为 `test`，在 `enable_testing()` 后与 CMake 保留名冲突（构建报 "The target name \"test\" is reserved"），已改名 `test_api`。

## 注意事项

- 运行期需要内核开放 `perf_event` 接口（`perf_event_paranoid`）；`tests/validate` 对宿主不存在的 PMU 用
  `LIBPFM_ENCODE_INACTIVE=1` 走静态校验，不需要真实硬件计数器
- 交叉编译验证在 x86_64 宿主上完成（无法执行 aarch64 二进制时，运行期行为以静态校验为准）
- 下游升级时注意：只要上游仍用 `__WORDSIZE` 判定字长，同一补丁需要重新生成（可优先推动上游采纳 LP64 宏）

---

## 结束标记

- **最终状态**：适配完成，归档状态 `built`（编译通过 + 配方验证通过 + 本地 CI 模拟通过，等待 CI 发布）
- 上游测试：85/85 通过（0 失败）；`test_package`：183/183 通过（0 失败、0 跳过）
- 本地 CI 模拟（W3）：exit_code=0（`.ci-result.json` 含日志 SHA256）；Pre-PR 独立审计：verdict=pass（P0/P1 清零）
- 补丁：2 个公共头可移植 LP64 修复，无平台宏；`tests/` 上游测试源码零修改
- 知识沉淀：E580（musl `__WORDSIZE` 缺失 → ABI 常量退化）、E581（`uname -s`=HarmonyOS → 源文件静默漏编）草稿随 PR 提交
- 编译结束。
