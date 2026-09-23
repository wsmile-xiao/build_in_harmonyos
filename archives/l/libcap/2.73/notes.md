# libcap 2.73 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

```bash
make -j1 CC=clang AR=llvm-ar RANLIB=llvm-ranlib GOLANG=no PAM_CAP=no SHARED=no
make -j1 test CC=clang AR=llvm-ar RANLIB=llvm-ranlib GOLANG=no PAM_CAP=no SHARED=no
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `mkcapshdoc.sh: No such file or directory` | `/bin/bash` 在 OpenHarmony 不存在 | shebang 改为 `#!/usr/bin/env bash`，由 PATH 解析（实测 `command -v bash` → `/data/service/hnp/bin/bash`，`/usr/bin/env` 存在） |
| 2 | `install: No such file or directory` | OpenHarmony 缺少 coreutils install | Conan `package()` 使用 `copy()` 安装头文件和库 |
| 3 | 语言预检识别为 Go | 上游同时包含 Go 模块和 C 库 | 按混合源码处理，配方仅交付 C 库并设置 `GOLANG=no` |

## 源码修改

- `0001-progs-mkcapshdoc.sh.patch`: 将 `progs/mkcapshdoc.sh` 的 shebang 改为 `#!/usr/bin/env bash`。仅改解释器寻址方式，不引入平台宏、不硬编码设备路径，属于 R8 允许的可移植性修复。

## 平台适配分析

libcap 的 C 交付物（`libcap.a`、`libpsx.a`）只依赖 POSIX API 与内核 capability 系统调用（`capget`/`capset`/`prctl`），不涉及图形、多媒体、外设或 HAL，因此不需要 `#ifdef __OHOS__` 类平台分支，补丁仅为解释器寻址修复。

实测证据（同一构建树，OpenHarmony 原生 clang）：

- `cap_test` 覆盖 `prctl` 错误边界（`cap_get_bound(-1)` 期望 `EINVAL`）、cap_t 分配/释放和 launcher 结构，全部通过；
- `psx_test` 在多线程与 fork 场景下验证 syscall 的 POSIX 语义传播（W3 归档日志 `reports/w3-local-ci.log` 中 `iteration [34388]: 0..9`、`./psx_test PASSED`；早期探索构建同路径日志为 `iteration [29931]: 0..9`），证明 libpsx 在 OHOS 线程模型下工作正常；
- `libcap_psx_test` 验证 libcap 与 libpsx 联合链接（`hello libcap and libpsx .......... PASSED`）；
- Conan 消费者测试直接调用 `cap_get_bound(CAP_CHOWN)`（进入 `prctl(PR_CAPBSET_READ, ...)` 路径）与 `cap_get_proc()`（进入 `capget` 系统调用路径），并验证两者在 OHOS 上成功返回；同时验证 `psx_set_sensitivity(PSX_IGNORE)`。这覆盖了包对内核 capability ABI 和线程辅助库的关键边界，而非仅做字符串转换。

依赖 root 的能力（文件 capability、chroot、user namespace）无法在 clean worker 上验证，已在下方逐项记录为未运行并注明原因；这不涉及当前交付的用户态库 API 与非特权 capability 查询路径。

## 上游测试清点

标准 `make test` 执行 3 个上游测试：`cap_test`、`psx_test`、`libcap_psx_test`（3/3 PASS）。`make sudotest` 另有 5 组特权场景：`uns_test`（root user namespace/capability）、`libcap_launch_test`（root/chroot/静态 libc）、`libcap_psx_launch_test`（root/chroot/pthread capability 传播）、`exploit/noexploit`（root capability 成功/失败对照）、`quicktest.sh`（root 文件 capability 与系统管理工具）。已用 `make -n sudotest` 完成入口清点；当前 clean worker 不具备上述权限与完整静态 libc，故 5 组均未运行（0/5，N/A），未计入标准 `make test` 的通过率。

## 依赖版本

无外部 Conan 依赖。

## 验证结果

```text
cap_test PASS
./psx_test PASSED
hello libcap and libpsx .......... PASSED
```

## 交付物

- `libcap.a`
- `libpsx.a`
- `sys/capability.h`
- `sys/psx_syscall.h`

## 注意事项

上游 `sudotest` 的 5 组场景需要 root user namespace、chroot、文件 capability 和完整静态 libc 的专用环境，不属于标准 `make test`，本次未运行并已逐项登记原因。
---

**编译结束**: 2026-09-03 22:38
**最终状态**: built
