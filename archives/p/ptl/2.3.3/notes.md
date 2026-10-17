# ptl 2.3.3 适配笔记

## 编译环境

- 构建系统：CMake
- 编译日期：2026-09-29
- 编译器：OHOS clang/clang++ 15，libc++，C++17
- 目标：HarmonyOS PC arm64
- 状态：built

## 上游测试清点与实测

上游没有独立 `tests/` 目录，而是由 `pyctest-runner.py` 注册示例程序作为正式测试。启用 TBB 时共注册 6 项：`tasking`、`recursive_tasking`、`minimal`、`tbb_minimal`、`tbb_tasking`、`recursive_tbb_tasking`。

原始源码在现代 GCC 15 下构建测试时因 `Backtrace.hh` 缺少 `<cstring>` 而失败；应用最小源码补丁后，上游 6 项测试全部实际运行通过。Conan 配方在每次构建中继续编译并运行相同 6 项，避免仅编译示例而不执行。

## 编译步骤

```bash
conan create archives/p/ptl/2.3.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=ptl/2.3.3
```

关键 CMake 选项：构建共享库，启用 TBB、线程锁和上游示例测试，同时关闭重复的静态库产物。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 示例测试编译报 `strlen` 未声明 | `Backtrace.hh` 直接调用 `strlen`，但未包含 `<cstring>` | 增加标准头文件 `<cstring>`；该问题与平台无关，也是上游 2.3.3 的已知现代编译器回归 |
| 2 | OHOS 编译报 `pthread_setaffinity_np` 未声明 | HarmonyOS 提供标准的 `sched_setaffinity`，但不提供 Linux pthread 非标准扩展 | 通过 CMake 检测可用接口；缺少 pthread 扩展时由工作线程自身调用 `sched_setaffinity(0, ...)`，保持线程亲和性功能 |
| 3 | 消费者编译缺少 TBB 公共头文件 | PTL 的公开头文件暴露 TBB 类型，依赖必须向消费者传播 | 在 Conan requirement 中声明传递头文件与库依赖，并导出 `tbb::tbb` 目标关系 |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`、`0002-cmake-Templates-Config.hh.in.patch`：检测并导出线程亲和性 API 能力。
- `patches/0003-source-PTL-Backtrace.hh.patch`：为 `Backtrace.hh` 增加 `<cstring>`，不修改任何测试逻辑。
- `patches/0004-source-PTL-ThreadPool.hh.patch`、`0005-source-ThreadPool.cc.patch`、`0006-source-Threading.cc.patch`：在缺少 pthread 扩展时从工作线程内使用 `sched_setaffinity`。

## 依赖版本

- `tbb/2023.0.0.1`：已发布到 ohpcd Conan 制品仓。
- `Threads`：HarmonyOS 系统线程库，由 CMake 检测。

## 验证范围

- 上游测试：6/6。
- Conan 消费者断言：7/7，其中 1 项为 HarmonyOS 专有的 PTL CPU/线程拓扑查询验证。
- 总计：13/13。
---

**编译结束**: 2026-09-29 02:37
**最终状态**: built
