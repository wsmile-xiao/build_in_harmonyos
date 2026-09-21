- **三方库名称**：jattach
- **上游版本**：v2.2
- **上游仓库地址**：https://github.com/jattach/jattach
- **适配路径**：路径 A（基础适配，无补丁）
- **使用知识库**：E002（/tmp 只读 erofs）、E461（OHOS 拒绝 AF_UNIX 文件 socket bind 的能力矩阵）、E246（HarmonyOS seccomp 拦截 syscall 触发 SIGSYS）；源码零修改，未新增知识草稿（本次无新错误模式）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游 tag tarball 无 tests/ 目录；Makefile 无 check/test 目标 |
| 集成测试 | 0 | 同上 |
| 其他测试 | 0 | 同上 |
| **合计** | **0** | 清点证据：`make -n check` → `No rule to make target 'check'`；tarball 仅 11 个文件（Makefile/README/LICENSE/jattach.spec/src/），详见 `notes.md` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无测试套件 |
| 集成测试 | 0 | 不变 | 上游无测试套件，未新增通用集成测试 |
| 鸿蒙特有测试 | 18 | 新增 | `test_package/test_jattach.sh` 消费者测试（CLI 契约 + /proc 进程查找 + HotSpot attach 触发路径 + AArch64 ELF 产物校验），18 条断言全部在鸿蒙 PC（HarmonyOS 6.1.0 / Kernel 1.12 aarch64）实机执行，按平台特有测试口径全部计入本行 |
| **合计** | **18** | **+18** | 上游 0 项 + 新增 18 项鸿蒙消费者用例（即鸿蒙特有测试行，不重复计数） |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例（上游无测试用例；源码零修改、零补丁）
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为 jattach CLI 补全 18 条消费者断言 —— 用法横幅/版本/退出码、非法
>   PID（非数字、0）校验、缺失进程 `/proc` 查找诊断、真实 HotSpot attach 触发路径
>   （目标进程 cwd 下 `.attach_pid<PID>` 创建被观测 → SIGQUIT 交付（目标以 handler 退出码 7
>   证明）→ 触发文件清理）、AArch64 ELF 产物校验。
> - **补全原因**：上游仓库 2.2 仅含 Makefile/README/LICENSE/jattach.spec 与 src/（11 文件），
>   无任何自动化测试（R51 三步法清点证据见 `notes.md`）。
> - **新增测试文件清单**：
>   1. `test_package/test_jattach.sh` — 18 断言消费者测试脚本（真实执行安装后的二进制）
>   2. `test_package/conanfile.py` — 通过 `conanrun` 环境驱动测试脚本（R34）

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：不适用（上游 N=0，清点证据见上表与 `notes.md`）
- 新增测试用例通过率：18/18（100%）

## 补充说明

- **源码零修改（无补丁）**：OHOS clang 15.0.4 定义了 `__linux__` 与 `__NR_setns` 并提供
  `<sys/ipc.h>`/`<sys/sem.h>`，`src/posix/psutil.c` 的 Linux 分支（含 setns 容器支持）
  与 OpenJ9 代码路径均原样编译；`conandata.yml` 声明 `patches: {}`。
- **已知限制（如实记录，非适配缺陷；详见 `notes.md`）**：
  1. HarmonyOS HMMAC 拒绝非应用进程创建 AF_UNIX 路径 socket（HMDFS EPERM；abstract socket
     可用），JVM 侧 attach socket 的正路径无法在设备 shell 会话内复现（E461）；
  2. SysV 信号量 `semget/semop` 被内核以 SIGSYS 终止，OpenJ9 attach 路径在本平台不可用
     （E246 / SysV IPC 草稿）；HarmonyOS 无 JVM 运行环境，该分支实际不可达。
- 编译验证（conan-verify G0–G4）、本地 CI 门禁结果见 `reports/test-report.md` 与
  `reports/conan-verify-report.md`。
