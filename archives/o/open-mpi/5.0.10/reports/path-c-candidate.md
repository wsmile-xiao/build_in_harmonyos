# OpenMPI 5.0.10 路径 C 候选说明

本说明仅申请将 OpenMPI 5.0.10 的 OpenHarmony 适配作为路径 C（高难度挑战）候选评估，不申报最终分值、最终验收或多进程 MPI runtime 结论。最终路径分类、验收和分值由评审决定。

## 适配范围与高难度说明

Open MPI 5.0.10 使用嵌套 Autotools 构建链，包含 PMIx、PRRTE、libevent、hwloc 与 ROMIO 等组件。OpenHarmony aarch64 真机验证还受到应用沙盒限制，因此不能仅以 host 构建结果推导目标侧行为。

本次适配涉及 OHOS aarch64 交叉构建、运行时动态加载、共享内存后端选择与应用沙盒限制。有效验证需要在真机完成，而非仅确认配方能够编译。

## 真机诊断与最小修复

上游 `make check` 中的 `dlopen_test` 曾收到 `SIGSYS`。由于真机缺少 syscall tracing 工具，使用带 flush 的分段运行时探针逐步定位：故障位于 `opal_shmem_base_select()`；POSIX `shm_open()` 探测成功，而 System V IPC `shmget()` 探测被 OpenHarmony sandbox 拒绝并触发 `SIGSYS`。

修复仅禁用不可用的 SysV shared-memory 后端运行时探测，POSIX shared memory 与 mmap 后端继续保留。未跳过或删除任何上游 `make check` 测试用例。

## 实际真机验证

| 项目 | 实际结果 | 说明 |
| --- | --- | --- |
| 真机 L0-L5 | 通过 | preflight=0，setup=0，CI=0 |
| configure、make、package | 通过 | OHOS aarch64 上创建 Conan 包 |
| 上游 `make check` | 通过 | TOTAL=3，PASS=3，SKIP=0，FAIL=0 |
| 已安装包消费者测试 | 通过 | singleton MPI 输出 `rank=0 size=1` |
| 补丁整洁与产物完整性 | 通过 | L4、L5 均通过 |

## 已知边界

不宣称多进程 MPI 已验证。设置正确 `OPAL_PREFIX` 后，`mpirun -np 2` 能进入 PRRTE 进程启动阶段，但 OpenHarmony application sandbox 会以 `SIGSYS` 终止被启动的 rank。未设置 `OPAL_PREFIX` 时，launcher 无法定位已安装的帮助文件。

前者为真实真机 sandbox 边界；两种结果均不计为多进程 MPI 通过。

## 可复用知识

本次可复用的诊断模式为：在真实 target 复现问题；当 syscall tracing 不可用时使用 flush 的分段探针；区分可用和不可用的后端探测；仅对不可用后端实施最小降级；最后重跑未修改的上游测试集和包消费者测试。

## 请评审确认

嵌套构建链、真机 SysV IPC 精确诊断、最小后端降级、完整 L0-L5 验证以及已记录的多进程 sandbox 边界，是否满足路径 C 候选材料要求？
