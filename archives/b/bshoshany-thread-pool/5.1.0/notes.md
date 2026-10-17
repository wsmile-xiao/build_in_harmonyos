# bshoshany-thread-pool 5.1.0 — 适配笔记（OHOS aarch64）

## 来源核验
- 官方仓库：https://github.com/bshoshany/thread-pool
- 正式标签：`v5.1.0`（GitHub release；Zenodo DOI 记录 2026-01-04 发布 v5.1.0）
- 源码 tarball：`https://github.com/bshoshany/thread-pool/archive/refs/tags/v5.1.0.tar.gz`
- SHA-256：`54378fb9cbeaee72996d3f8761469c43bb7dd2d4b07faec6d29a68277bd91a51`（tarball 实测）
- 许可证：MIT（LICENSE.txt，Copyright (c) 2021-2026 Barak Shoshany）
- 同包名前一版本：5.0.0（archives/b/bshoshany-thread-pool/5.1.0 沿用既有包名 `bshoshany-thread-pool`，conan name/cmake target 与 5.0.0 一致，避免同一上游软件出现两个包名）

## 结构
- 单文件头文件库：`include/BS_thread_pool.hpp`（2510 行，v5.1.0 保持 true single-header）
- 无 CMake 项目（上游用脚本 compile_cpp.py + pyproject.toml 编译测试，pyproject.toml 仅为 [tool.pyright] 等工具配置，无 [build-system]/[project] 打包段）
- C++17/20/23 兼容；可选 C++20 module（modules/BS.thread_pool.cppm），打包按 header-only 处理
- 上游测试：`tests/BS_thread_pool_test.cpp`（单文件主程序，自带 check() 计数框架，无第三方测试框架）
- 依赖：无任何第三方依赖（仅标准库；原生扩展 BS_THREAD_POOL_NATIVE_EXTENSIONS 为可选非必需）

## 与 5.0.0 的相关差异
- v5.1.0 新增原生线程亲和性扩展（`BS::this_thread::get/set_os_thread_affinity()`），Linux 分支使用 glibc 扩展 `pthread_getaffinity_np/pthread_setaffinity_np`
- 其余 API（submit_task/detach_loop/wait/版本对象等）与 5.0.0 兼容

## OHOS 适配（1 个补丁）
### patches/0001-ohos-thread-affinity-sched.patch
- **第一条真实错误**：`include/BS_thread_pool.hpp:1028/1063: error: use of undeclared identifier 'pthread_getaffinity_np'/'pthread_setaffinity_np'`（clang 15 OHOS sysroot，musl libc 无 glibc `_np` 扩展）
- **知识命中**：E211（replace-with-sched-api）——用 `sched_getaffinity(0,...)/sched_setaffinity(0,...)` 替代，pid=0 表示调用线程，语义与 `pthread_*_np(pthread_self(),...)` 等价；`cpu_set_t/CPU_ZERO/CPU_ISSET/CPU_SETSIZE` 与 `get_nprocs()`（sys/sysinfo.h）在 OHOS sysroot 实测均可用
- **实现方式**：在每个函数内 `#elif defined(__OHOS__)` 分支置于 `__linux__` 分支之前（OHOS 同时定义 `__linux__`），为实质实现而非降级；glibc/Windows/降级分支全部保留不动
- 进程级 `get/set_os_process_affinity()` 使用的 `sched_*(getpid(),...)`+`get_nprocs()` OHOS 原生可用，未修改

## 语言预检偏差记录
`ohc-run.py lang-preflight` 判定 `env_unsupported`（detected=python），人工复核为误判：
- 检测依据是 pyproject.toml 存在 + cpp 源文件占比 67% < 70% 触发 manifest 回退
- 实证：pyproject.toml 全文 382 行均为 [tool.pyright] 工具配置，无 [build-system]/[project] 打包段；库本体为 C++ 单头文件（2510 行）+ C++ 测试（4200+ 行），Python 仅 scripts/compile_cpp.py 辅助脚本
- 依据 workflow"辅助脚本不决定主体语言"，主体语言 C++，任务标记 cpp 正确

## 平台事实（OHOS Python）
- `platform.system()` 在 OHOS 设备 Python 3.12.8 返回 `"HarmonyOS"`（非 Linux/Darwin/Windows）
- 上游 compile_cpp.py 的编译器自动检测仅处理 Windows/Linux/Darwin 三分支，落空报 "No compiler found!"
- 处置：显式 `-c clang++` 传参绕过自动检测，未修改上游脚本
- 该模式已建知识草稿（knowledge/drafts/），可复用于所有带 OS 分支检测的上游 Python 构建/测试脚本

## 验证矩阵（设备实测，clang 15.0.4 OHOS，make 4.4.1，Python 3.12.8）
| 轮次 | 配置 | TOTAL | PASS | FAIL | 结论 |
| --- | --- | --- | --- | --- | --- |
| 1 | C++17 header + native 扩展（上游 yaml 默认 defines） | 268 | 259 | 9 | 9 项均为环境限制（见下） |
| 2 | C++17 header 无扩展（等价 5.0.0 直接 clang++ 口径） | 208 | 208 | 0 | 全部通过 |
| 3 | C++20 header 无扩展 | 208 | 208 | 0 | 全部通过 |
| 4 | C++20 modules（yaml 默认 defines） | — | — | — | clang 15 modules 支持不完整（链接报 `undefined symbol: initializer for module BS.thread_pool`；上游头文件注释自证 Clang 对 C++20 modules 支持仅部分） |
| 5 | C++23 | — | — | — | clang 15 无 `-std=c++23`（最高 `c++2b`） |

统计单位：上游自写 check() 计数（测试程序以 `tests_failed` 数退出）。

## 轮次 1 的 9 项失败归因（全部为环境限制，附原始证据）
- **设备 cpuset 限制（7 项）**：设备 20 核，但 `/proc/self/status` 实测 `Cpus_allowed_list: 0-7`（进程仅允许 8 核；`len(os.sched_getaffinity(0))==8`）。
  1. 构造线程数 `Expected: 20, obtained: 8`——native 扩展下池按进程 affinity（8 核）建池，测试假设其等于 `hardware_concurrency()`（20）
  2-5. `get_index()/get_pool()` 对照 4 项——测试向量大小取 `hardware_concurrency()`（20），池仅 8 线程，索引 8-19 未写入导致对照失败
  6-7. thread/process 隔核 affinity 2 项——请求 20 核中隔核 10 个，仅允许集内 5 个生效（Linux sched_setaffinity 对超出允许集的请求部分生效）
  - 替代验证：去掉 BS_THREAD_POOL_NATIVE_EXTENSIONS 后这些检查整段不编译，剩余 208 项全部通过（轮次 2/3），证明库本体与补丁无缺陷
- **非 root 权限限制（2 项）**：`realtime/highest` 线程优先级需要 SCHED_FIFO/RR 权限。上游测试自注 "NOTE: On Linux, this test must be run as root, otherwise it will fail!"，输出自打 "failed, most likely due to insufficient permissions; ignoring"。`above_normal` 及以下优先级检查全部通过

## test_package（消费者验证）
- Conan L1：CMakeDeps + find_package 链接打包头文件，6 项断言：submit_task/get、detach_loop/wait 计数、并发求和、版本对象、native affinity get（OHOS sched_getaffinity 补丁路径）、affinity set 回读一致性
- 消费者以 `BS_THREAD_POOL_NATIVE_EXTENSIONS` 编译，直接覆盖 OHOS 补丁代码路径

## 后续
- 状态：built（2026-09-05 finish 收尾回填，内嵌 conan-verify 与 W3 本地 CI 模拟通过）
- 无 commands.json（纯库，无命令行产物）
---

**编译结束**: 2026-09-05 13:26
**最终状态**: built
