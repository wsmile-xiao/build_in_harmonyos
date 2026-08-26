# liblbfgs 1.1 适配知识草稿

## 适用范围

这份草稿只记录 `liblbfgs/1.1` 本轮 HarmonyOS 适配中确认过的事实、踩坑和处理方式，不作为其他 L-BFGS 实现或其他 liblbfgs 版本的通用结论。`liblbfgs` 的 1.1 API 和后续常见版本有差异，复用时要先核对头文件。

## 上游版本指纹

- 上游主页：`https://www.chokkan.org/software/liblbfgs/`。
- 1.1 源码包：`https://www.chokkan.org/software/dist/liblbfgs-1.1.tar.gz`。
- SHA256：`5b71d193a5f44ce958f123f6ae58be4355547cbf722a50d2aaf06eda1c69de23`。
- 这个 tarball 解压后没有顶层目录，直接得到 `COPYING`、`include/`、`src/`。Conan `get()` 需要使用 `strip_root=False`。
- 源码包没有 `configure`、`Makefile`、`CMakeLists.txt` 等构建系统文件，不能按 autotools 或上游 CMake 项目处理。

## 源码结构判断

- 公共头文件是 `include/lbfgs.h`。
- 库实现文件是 `src/lbfgs.c`。
- 上游示例是 `src/main.c`。
- 实际打包只需要安装 `include/lbfgs.h`、`lib/liblbfgs.a` 或共享库，以及 `COPYING` 许可证。
- `src/main.c` 可以作为编译覆盖，但不适合直接作为运行测试。

## 1.1 API 差异

`liblbfgs` 1.1 不能直接套用新版示例或 ConanCenter 里可能见到的新版调用方式：

- `lbfgs()` 签名没有 `ptr_fx` 输出参数。
- 没有 `lbfgs_malloc()` 和 `lbfgs_free()` helper。
- 测试程序可以直接使用栈数组，例如 `lbfgsfloatval_t x[2]`。
- 回调签名使用 `evaluate(void *instance, const lbfgsfloatval_t *x, lbfgsfloatval_t *g, const int n, const lbfgsfloatval_t step)`。
- 调用形式应为 `lbfgs(2, x, evaluate, progress, &state, &param)`。
- 优化结束后的目标函数值需要自己再调用一次 `evaluate()` 计算，不能从 `lbfgs()` 参数取回。

测试里不要只检查链接成功。至少应覆盖 `lbfgs_parameter_init()` 默认值、evaluate 回调执行、progress 回调路径、优化返回码、最终点位和目标函数容差。

## 生成 CMake 包装的理由

由于 1.1 源码包没有构建系统，recipe 在 `generate()` 阶段写入一个最小 CMake 工程。这个做法有几个好处：

- 不需要把构建系统补丁混入上游源码 patch，patch 可以只保留真正的源码兼容性修正。
- Conan 的 `CMakeToolchain`、`cmake_layout()`、`CMakeDeps` 能正常参与构建和 test_package。
- 同一套 recipe 可以覆盖 Linux/OHOS 的静态库和共享库构建。
- 可以在构建树里增加 `test_liblbfgs_build.c`，用 `ctest` 做 build-time smoke test。

需要注意：库包不应该安装运行程序。`install(TARGETS lbfgs ...)` 只保留 `ARCHIVE DESTINATION lib` 和 `LIBRARY DESTINATION lib`，不要写 `RUNTIME DESTINATION bin`。本轮第一次 shadow CI 的 L0 就因为出现了 `bin/` 相关安装意图而触发 `commands_json_r38`。

## OHOS/clang 兼容性点

本轮实际需要两个 patch 点：

- `src/lbfgs.c` 使用 `memcpy()`，但缺少 `#include <string.h>`。现代 clang 下应显式包含。
- `src/main.c` 的入口写成 `int main(int argc, char *argv)`，OHOS clang 把第二参数类型错误当作编译错误。应改为 `int main(int argc, char **argv)`。

`src/lbfgs.c` 中 `if (ret = proc_progress(...))` 会产生 clang warning，但它是上游原有赋值式检查，本轮没有改动语义。除非后续有明确质量要求，不建议为了消 warning 扩大 patch 面。

## 为什么示例只编译不运行

上游 1.1 的 `src/main.c` 在优化结束后调用 `evaluate(NULL, x, NULL, N, 0)`，而 `evaluate()` 内部会写 `g[i]`。这里的 `g == NULL` 会导致空指针写入风险。因此：

- 可以把 `src/main.c` 编译成 `liblbfgs_sample`，用于覆盖示例源文件能否通过 OHOS clang。
- 不应把上游示例作为 smoke test 执行。
- 运行测试应使用 recipe 生成的 `test_liblbfgs_build.c` 和 `test_package/test.c`，两者都给 evaluate 提供有效梯度数组。

## test_package 设计经验

`test_package` 采用一个二维凸二次函数：最优点 `(1.0, -2.0)`。这种测试足够小，适合真机 CI，又能证明库不是只完成了链接：

- 初始点离最优点较远，可以触发多次 evaluate/progress。
- 梯度解析简单，避免测试本身引入数值误差。
- `ret < 0` 视为失败，非负返回继续检查最终目标函数和点位。
- 输出固定 smoke evidence：`liblbfgs/1.1 smoke test passed: ret=0 fx=0 progress=2`。

shadow CI 的 L1e destructive negative test 会临时移走 `lib/` 和 `include/`，本轮已经确认 test_package 会因此失败，说明测试确实依赖打出来的包。

## shadow CI 复盘

本轮使用真机：`currentUser@10.62.220.52:2222`。

通过的 shadow run：

- 外层 run：`/storage/Users/currentUser/ohos-test-runs/codex-liblbfgs-shadow-ci-1.1-r4-20260825-220817-65005`。
- shadow run：`/storage/Users/currentUser/ohpc-ci-shadow/runs/20260825T141501Z-fb1712a8ac-3539`。
- 临时 commit：`fb1712a8acdb37a80eefbf848be7f85d0a8b97fa`。
- 结果：exit 0；`G0/L0/L1/L4/L5` pass；`L2` 因无 `bin/` skip。
- device package revision：`6ada7caf82c69cae04905deec79d7885`。

前两次失败有明确价值：

- r1 失败在 L0，提醒库包不要暴露 `bin/` 安装路径，也不需要 `commands.json`。
- r3 失败在 L1 编译上游 sample，提醒 `main` 参数类型即使只是 sample 也会被 OHOS clang 严格检查。

## 后续维护清单

改这个包时建议按下面顺序回归：

- 确认只改 `archives/l/liblbfgs/1.1`。
- 清理本地生成物，尤其是 Python `__pycache__`、Conan build/cache 临时目录和 test_package build 目录。
- 跑 YAML/Python 解析和 whitespace check。
- 跑 `ci/conan/detect_bindirs.py archives/l/liblbfgs/1.1/conanfile.py`，期望输出 `0`。
- 如果改了 patch 或 recipe 生成 CMake，重新跑 `conan source` 确认 patch 能应用。
- 真机侧重新跑单包 shadow CI，不要和依赖库或其他库混跑。
- 提交时只 add `archives/l/liblbfgs/1.1`，不要带入同一 worktree 里已有的 `archives/l/libXext/*` 脏文件。

## PR 交接要点

PR 描述建议保留这些高信号信息：

- `liblbfgs/1.1` 是 raw C source，无上游构建系统，recipe 生成最小 CMake wrapper。
- patch 只处理 `string.h` 和 sample `main()` 签名两个兼容性问题。
- sample 编译但不运行，运行验证由 build-time test 和 test_package 提供。
- 真机 shadow CI 已通过，run dir 为 `20260825T141501Z-fb1712a8ac-3539`。
- `L2 skip` 是预期行为，因为该包是 library package，没有 `bin/`。
