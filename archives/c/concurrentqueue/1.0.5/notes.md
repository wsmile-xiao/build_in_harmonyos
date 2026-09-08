# concurrentqueue 1.0.5 — 适配笔记（qzy/concurrentqueue）

## 任务与来源核验
- 任务号：#5903（开源鸿蒙PC专项积分赛-依赖，分支 feat/concurrentqueue-1.0.5）
- 官方仓库：https://github.com/cameron314/concurrentqueue
- 正式标签：`v1.0.5` → commit `9afb99746f0f5fc94ac8aef737053ae0481ba8d1`
- 源码 tarball：`https://github.com/cameron314/concurrentqueue/archive/refs/tags/v1.0.5.tar.gz`
- SHA-256：`4d6368a27492d86011fde5ca0cf386dce7c49cd425aa3d9b063ca6ec373a6ef3`
- 许可证：Simplified BSD License（BSD-2-Clause）
- worktree：`~/qzy/concurrentqueue`，基线 upstream/main `89f8a53a79`

## 与 1.0.4 的差异（W0b 历史经验核验）
- 已归档 1.0.4（PR !7193，junshi_liu）：CMake INTERFACE header-only，配方直接迁移，仅版本/URL/SHA 变化。
- 1.0.5 新增 `c_api/` 目录（C 绑定封装，`concurrentqueue.cpp`/`blockingconcurrentqueue.cpp`），上游 unittests 现在编译并链接这两个翻译单元（`build/makefile` 的 bin/unittests 依赖）。
- 头文件与安装布局不变：`include/concurrentqueue/moodycamel/`，CMake 包名 `concurrentqueue`，target `concurrentqueue::concurrentqueue`。
- 历史结论"无第三方依赖、CMake INTERFACE、头文件装到 moodycamel 子目录"在 1.0.5 逐项比对仍成立，配方未偏离。

## W0 依赖检查
- header-only，无第三方依赖。`ci/scripts/preflight_check.sh concurrentqueue/1.0.5` 通过（无依赖需要检查）。

## 语言/构建系统预检（R47）
- `lang-preflight`：detected=cpp，与任务声明一致，通过（无顶层 pyproject.toml/setup.py，构建系统 CMake）。

## 上游测试清点（R51 第一步，按 v1.0.5 源码静态统计）
| 测试入口 | 静态用例数 | 说明 |
| --- | --- | --- |
| tests/unittests（minitest.h 框架，`REGISTER_TEST` 注册） | 45 | 上游主测试套件，`build/makefile` 的 `bin/unittests` |
| tests/fuzztests | 0（无限随机循环，无固定用例数） | 随机 seed 循环直到失败，非固定回归套件 |
| tests/relacy | 需 Relacy 竞争检测器（Windows 专用框架） | OHOS 不可运行 |
| tests/CDSChecker | 需外部 CDSChecker 工具链 | OHOS 不可运行 |

上游 CMakeLists.txt 无测试 target；官方测试入口是 `build/makefile`（`make tests`）。

## 上游测试实际执行（R51 第二步，设备真机）
- 构建等价性说明：`build/makefile` 硬编码 `g++`，OHOS 设备无 g++；按上游编译行逐命令将 `g++` 替换为 `clang++`（OHOS 15.0.4），其余参数完全一致（`-std=c++11 -Wall -pedantic-errors -Wpedantic -Wconversion -DMOODYCAMEL_STATIC -pthread -g -O0 -fno-elide-constructors`，c_api 两个翻译单元加 `-fno-exceptions`）。
- `bin/unittests`（默认 8 iterations）：
  - 静态注册 45；实际执行 45；passed 45；failed 0；skipped 0。
  - 输出尾部：`All tests passed.`，退出码 0。
  - 证据：`~/tmp/uc2/concurrentqueue/upstream-tests.log`（run2 段）。
- `bin/fuzztests`（补充证据，非回归门禁）：`clang++` 等价构建成功；bounded 运行 90 秒无失败（timeout 124 截断属预期，随机 fuzz 无固定用例数，不计入回归表）。
- CDSChecker / relacy：外部专用工具链（模型检测/Windows 竞争检测），CI 与设备均无法提供，记为未执行，不影响 unittests 主套件 45/45 的完整性。

## test_package（消费者测试）
- 3 项断言：单线程 enqueue/try_dequeue 1000 条全数出队；多线程生产者-消费者 10000 条全数消费；头文件包含与链接。
- 通过 `self.tested_reference_str` 引用被测包，CMakeDeps + find_package(concurrentqueue)。

## 首轮 Adapt / 本地验证
- conan create（conan-verify）通过，test_package 运行 PASS（见 reports/test-report.md）。

**最终状态**: built
---

**编译结束**: 2026-09-05 22:19
**最终状态**: built
