# ctrl-c 1.0.0 适配笔记

## 编译环境
- 构建系统: cmake（上游无构建系统，`CMakeLists.txt` 由配方提供并 `exports_sources`）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4 / clang++（OHOS aarch64 profile，libc++）
- 状态: built

## 编译步骤

1. `source()`：按 conandata 下载官方 tag 归档
   `https://github.com/evgenykislov/ctrl-c/archive/refs/tags/v1.0.0.tar.gz`
   （sha256 `9f63ff2e…5ee1a` 校验通过），`strip_root=True` 解到 source folder。
2. `generate()`：`CMakeToolchain` 注入 `-DBUILD_SHARED_LIBS=OFF`（默认静态）与
   `-DCMAKE_POSITION_INDEPENDENT_CODE=ON`（fPIC）。
3. `build()`：`cmake.configure(build_script_folder=self.export_sources_folder)` 用包目录内的
   包装 `CMakeLists.txt`（上游 tag 里没有根 CMakeLists，README 明示"把源文件拷进你的工程"），
   目标 `ctrl-c` 编译 `src/ctrl-c.cpp`（C++11）。
4. `package()`：`cmake --install` 落 `lib/libctrl-c.a` + `include/ctrl-c.h`，并拷贝上游 `LICENSE`
   到 `licenses/`。
5. `test_package`：`find_package(ctrl-c CONFIG REQUIRED)` → 链接 `ctrl-c::ctrl-c` →
   `test()` 以 `self.run(..., env="conanrun")` 执行 `bin/test_ctrl_c`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 解出的 `.orig`/`.work` 只剩 `test/`（`src/ctrl-c.{cpp,h}`、LICENSE、README 全丢） | `scripts/ohc/init_build.py` 的 `_promote_nested_source` 把「唯一带构建标记的子目录」`test/CMakeLists.txt` 当成源码根，提升时删除了同级其余目录 | 按原 tarball 重解 `.orig`、复制出 `.work` 并用 `edit_tracker.snapshot()` 重建 8 文件基线；已记 `feedback/pending/` |
| 2 | 上游测试是交互式示例（等 3 次 Ctrl+C 按键），无法在 `conan create` 里直接跑 | `test/main.cpp` 用 `condition_variable` 等外部投递的 SIGINT | 上游测试在设备沙箱 HOME 下由外部 SIGINT 驱动脚本喂 3 次信号跑通；`test_package` 用进程内 `raise(SIGINT)` 非交互复现同一 API 面 |
| 3 | 消费者测试初版 case5 报 `sa_handler != SIG_DFL` | 自身用例 bug：case1 注册的 handler 未释放，handler 列表未清空 ⇒ 库未恢复 SIG_DFL | case2 结束时 `ResetCtrlCHandler(id1)`；现 6 用例全绿（该读数也正向证明了「列表清空才恢复 SIG_DFL」的语义） |

## 源码修改

无：`conandata.yml` 的 `patches: []`，上游两个源文件按原样编译（`git` 侧零补丁）。

## 依赖版本

0 依赖：仅 C++ 标准库（`<algorithm>/<mutex>/<list>/<functional>`）与 POSIX `<signal.h>`；
`<Windows.h>` 分支仅在 `_WIN32` 下编译。

## 验证结果

```bash
# 上游测试（沙箱 HOME，外部驱动 3 次 SIGINT，驱动脚本 run_with_sigint.py）
$ HOME="$TASK_DIR/test-home" python3 $TASK_DIR/upstream-test/run_with_sigint.py ./test-ctrl-c 3
Press Ctrl+C 3 times
Caught Ctrl+C
Caught Ctrl+C
Caught Ctrl+C
All Ctrl+C's pressed
driver: rc=0 sigints_sent=3

# 消费者测试（test_package/test_ctrl_c.cpp，6 用例 / 20 断言）
$ HOME="$TASK_DIR/test-home" ./test_ctrl_c
case0_packaged_header_fingerprint: PASS
case1_basic_signal_delivery: PASS
case2_repeated_delivery: PASS
case3_lifo_and_stop_propagation: PASS
case4_reset_single_handler: PASS
case5_reset_all_and_reinstall: PASS
cases=6 failed_cases=0 failed_checks=0
rc=0
```

（`conan create` 干净轮读数由 `conan_verify_round.sh` 证据副本覆盖，见 `reports/`。）

## 注意事项

- 库在内部互斥锁下回调 handler：handler 内不得调用 `SetCtrlCHandler`/`ResetCtrlCHandler`
  （上游 README 同款死锁警告），消费者测试的 handler 只碰普通变量。
- handler 列表清空后库把 SIGINT 恢复成 `SIG_DFL`，此时再投递 SIGINT 会终止进程——
  case5 用 `sigaction(SIGINT, nullptr, &query)` 查询代替真实投递。
- 本设备测试证据一律在沙箱 `HOME="$TASK_DIR/test-home"` 下执行，不写用户真实 HOME。
