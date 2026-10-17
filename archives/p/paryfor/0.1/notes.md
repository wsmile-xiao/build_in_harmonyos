# paryfor 0.1 适配笔记

## 编译环境

- 构建系统：header-only（上游 CMake 只构建官方测试程序）
- 编译日期：2026-09-27
- 编译器：Clang 15 / C++14
- 目标：HarmonyOS PC aarch64
- 状态：built

## 源码与构建

- 官方仓库：`https://github.com/ekg/paryfor`
- 官方标签：`v0.1`（提交 `509b28a092f732a068e2908bb9e359a8562cd32f`）
- 官方归档 SHA256：`4b38606c0256a3cf34c06808a158339ed9b8e51e14c189025fd4effde004ecef`
- 配方安装 `paryfor.hpp` 与两份 MIT 许可证，不发布上游测试可执行文件。
- 无外部 Conan 依赖；线程支持由目标系统提供。

## 上游测试清点与实测

官方 v0.1 归档共 7 个文件；无 `tests/`、`test/` 目录，无 `add_test()`、CTest、
GoogleTest 或其他测试框架注册。唯一官方测试入口为根目录 `test.cpp`，由
`CMakeLists.txt` 构建为 `paryfor-test`。该程序执行带分块的 `parallel_for`，汇总
各工作线程处理数量并校验总数等于请求的迭代数。

| 上游入口 | 注册口径 | 实际命令 | 结果 |
|----------|----------|----------|------|
| `test.cpp` | 1 个独立测试程序 | `paryfor-upstream-test 1024 4 16` | 1/1 通过 |

- 上游测试总数：1
- 实际执行：1
- 通过：1
- 失败：0
- 通过率：100%

配方 `build()` 会用目标编译器重新编译官方 `test.cpp`；原生 HarmonyOS worker 上
签名后直接运行，并输出结构化 `HMBS_UPSTREAM_TEST_RESULT` 作为 CI 证据。

## 新增消费者测试

| 测试 | 检查数 | 覆盖范围 | 结果 |
|------|--------|----------|------|
| `test_paryfor.cpp` | 8 | 三种 `parallel_for` 重载、精确一次执行、求和、线程编号及原子队列 API | 8/8 通过 |
| `test_paryfor_ohos.cpp` | 6 | `__OHOS__`/AArch64 编译路径、AArch64 原子队列 FIFO/容量与并发压力 | 6/6 通过 |

适配后共有 3 个测试程序，15 个检查点；测试入口数和检查数均不少于上游实测。

## HarmonyOS 适配结论

上游 `paryfor.hpp` 已针对 `__aarch64__` 使用 `yield` 指令实现自旋等待，并且只依赖
C++14 标准库、原子操作与线程接口。上游 `AtomicQueue2` 的多生产者/多消费者路径
以 release store 发布槽位，却以 relaxed CAS 获取槽位所有权；该组合在 x86 上通常
被较强的硬件内存序掩盖，在 AArch64 上会允许消费者读取尚未同步的元素。补丁将读、
写两侧的所有权 CAS 成功序改为 acquire，与现有 release store 配对。ThreadSanitizer
修复前能稳定报告 `q_element` 读写竞争，修复后不再报告。目标构建、官方测试、通用
消费者测试及鸿蒙专有测试全部通过。

## 验证命令

```bash
conan create archives/p/paryfor/0.1 \
  -pr:h ci/conan/profiles/ohos-aarch64 \
  -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
python3 scripts/ohc-run.py conan-verify paryfor 0.1
python3 scripts/ohc-run.py finish paryfor 0.1 built
```

## 源码修改与依赖

- 源码补丁：`0001-atomic-queue-acquire-state-ownership.patch`，修复 AArch64 弱内存序下的队列元素发布竞态。
- 外部依赖：无。
- 包类型：header-library，不生成 `commands.json`。
