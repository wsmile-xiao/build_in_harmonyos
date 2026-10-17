# libomp-jonathonl 1.0.0 适配笔记

## 基本信息

| 项目 | 内容 |
|---|---|
| 上游仓库 | https://github.com/jonathonl/omp |
| 上游版本 | v1.0.0 |
| 源码 SHA256 | `839bcd55953b7711dbfd6716d5bcdf90a82ff4fa2ac384712775528cb1dc8284` |
| 构建系统 | CMake / Conan 2 |
| 目标平台 | HarmonyOS PC, arm64-v8a |
| 许可证 | MIT |
| 第三方依赖 | 无 |

## 上游测试盘点

上游没有 `tests/` 目录，也没有 CTest 注册项；`ctest -N` 的测试数为 0。源码根目录的 `main.cpp` 由 CMake 构建为 `omp-test`，是上游唯一可执行测试，因此上游实测总数为 1。该测试覆盖静态和动态 `parallel_for`、临界区、`thread_pool2` 与显式并行执行，实际执行结果为 1/1 通过，输出值为 `264`。

## 适配内容

- Conan 2 配方按静态库构建和打包，避免与 HarmonyOS SDK 自带 `libomp.so`/`libomp.a` 产生命名冲突。
- 配方构建阶段执行上游 `omp-test`，消费测试再次复现上游 `main.cpp` 的完整测试语义。
- 通过 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容当前 CMake 对旧版上游策略声明的要求。
- 补丁 `0001-include-omp.hpp.patch` 修正默认线程数路径：构造函数应使用已经解析完成的 `num_threads_` 预留线程容器；原实现使用值为 0 的入口哨兵并执行减一，导致 `std::bad_alloc`。
- 新增 HarmonyOS 专项测试，编译期校验 `__OHOS__` 与 AArch64，运行期覆盖 64 位 ABI、默认并行路径、pthread 调度查询、动态调度完整性和临界区互斥。

## 测试结果

| 测试组 | 数量 | 结果 |
|---|---:|---:|
| 上游源码测试 `omp-test` | 1 | 1/1 通过 |
| 移植后上游语义消费测试 `upstream_main` | 1 | 1/1 通过 |
| HarmonyOS 专项测试 `ohos_thread_runtime` | 1 | 1/1 通过（8/8 检查项） |
| 移植后 `test_package` 合计 | 2 | 2/2 通过 |

验证命令：

```bash
python3 scripts/ohc-run.py conan-verify libomp-jonathonl 1.0.0 \
  --project-dir .
```

HarmonyOS AArch64 构建、上游测试、消费测试和 HarmonyOS 专项运行测试均通过。

## 交付物

| 文件 | 说明 |
|---|---|
| `conanfile.py` | Conan 2 构建与打包配方 |
| `conandata.yml` | 上游源码校验与补丁声明 |
| `patches/0001-include-omp.hpp.patch` | 默认线程数分配修复 |
| `test_package/` | 上游语义消费测试及 HarmonyOS 专项测试 |
| `reports/conan-verify-report.md` | 官方 Conan 验证报告 |
---

**编译结束**: 2026-09-15 02:11
**最终状态**: built
