# DRAFT-libcorrect-0.0-git20260204-ctest-subdir-exclude-from-all — ctest 子目录注册 + EXCLUDE_FROM_ALL 双坑（libcorrect 0.0-git20260204 实证）

- 状态：pending-editor-review
- 关联 PR：#14383（commit e0908a3469）
- 实证构建：#68073 / #68167（OHOS aarch64，ctest 4/4 passed）

## 错误特征

上游源码树手动构建一切正常，但 conan 配方里最常见的两种测试写法都会得到**假绿**：

```
$ cd build && ctest
No tests were found!!!        # 退出码 0 —— 假绿
```

或者（runner 根本没被编译）：

```
$ ctest --output-on-failure
The test executable .../convolutional_test_runner does not exist
```

error_signature（正则，| 分隔）：

```
No tests were found!!!|test_runners EXCLUDE_FROM_ALL|enable_testing.*subdirectory|add_test.*not registered at root
```

## 触发条件

- 阶段: 配方 build() 的上游测试接入（W3/conan create 内）
- 前置（两坑叠加，libcorrect tests/CMakeLists.txt 是标准样本）：
  1. `enable_testing()` 写在 `tests/CMakeLists.txt` 而非顶层 `CMakeLists.txt` —— CTestTestfile.cmake 只生成在 `build/tests/`
  2. 每个测试可执行文件都是 `add_executable(... EXCLUDE_FROM_ALL ...)` —— 默认构建不编译
  3. 上游提供聚合目标 `add_custom_target(test_runners DEPENDS ${all_test_runners})`，且顶层有 `add_custom_target(check COMMAND ${CMAKE_CTEST_COMMAND} DEPENDS test_runners)`（上游 `make check` 的入口）

## 根因分析

CMake 的测试注册按目录进行：`add_test` 注册进**最近一层**调用了 `enable_testing()` 的目录的 CTestTestfile.cmake。根目录 `ctest` 只读根目录的 CTestTestfile.cmake —— 没有就一个测试都扫不到，**且以退出码 0 结束**。因此"根级 ctest + 退出码 0"不能当通过证据。

同时 EXCLUDE_FROM_ALL 使测试可执行文件不进默认 `all` 目标：只跑 `cmake --build` 再 ctest，会报 test executable does not exist。上游设计如此是为了让 `make` 默认只编库、`make check` 才编测试。

## 修复方案（solution）

```python
def build(self):
    cmake = CMake(self)
    cmake.configure()
    cmake.build()
    cmake.build(target="test_runners")   # 上游 make check 的等价物（聚合目标名先 grep 确认）
    self._run_upstream_tests()

def _run_upstream_tests(self):
    # 探测含 CTestTestfile.cmake 的目录（tests/ 优先，根目录兜底）
    dirs = [d for d in (join(self.build_folder, "tests"), self.build_folder)
            if isfile(join(d, "CTestTestfile.cmake"))]
    command = "ctest --output-on-failure"
    for ctest_dir in dirs:
        self.run(command, cwd=ctest_dir, env="conanrun", ignore_errors=True)
        marker = self._parse_ctest_log(self.build_folder, command)  # LastTest.log fail-closed
        if marker["status"] == "passed":
            return
    raise ConanException("upstream ctest failed: ...")
```

适配前三步探测（写进 notes.md 备忘）：

```bash
grep -n "enable_testing" CMakeLists.txt tests/CMakeLists.txt   # 位置：顶层 vs 子目录
grep -n "EXCLUDE_FROM_ALL" tests/CMakeLists.txt                # runner 是否排除在 all 外
grep -n "add_custom_target(test" tests/CMakeLists.txt          # 聚合目标名
```

计数唯一来源 `Testing/Temporary/LastTest.log`（在 build 树里**递归找**——cmake_layout 单配置在 `build/Release`，子目录测试再深一层，walk 限深 6）；解析沿用 libbgcode 的 fail-closed 口径：`N/M Testing:` 分母一致性 + `Test Passed.`/`***Test Failed.` 判决行 + 恒等式自检。

## 降级方案（fallback）

若上游没有聚合目标（无 add_custom_target(test_runners)）：用显式目标列表逐个构建（cmake.build(target="xxx_test_runner")；或 cmake --build --target help 列出后挑全部 *_test_runner）。若 ctest 子目录探测失败（无 CTestTestfile.cmake）：退回直接执行测试二进制并断言退出码 + 输出特征行，但统计表须如实标注口径为 direct-exec 而非 ctest_entries。**禁止用根级 ctest 退出码 0 当通过证据**。

## 查重与覆盖判断

- 查重关键词：ctest、No tests were found、EXCLUDE_FROM_ALL、test_runners、enable_testing、CTestTestfile
- 知识库现有最接近条目：E298（conanrun/VirtualRunEnv 与 ctest 运行环境——讲的是共享库运行路径，不是测试注册位置）；E022/E023（ctest 关键词命中但主题是 POSIX 信号量/locale）
- 覆盖判断：现有条目均未覆盖"enable_testing 子目录注册 + EXCLUDE_FROM_ALL 聚合目标"这一模式；本条增量在 CMake 测试注册的目录语义 + 上游 make check 入口的等价构建方式，可跨库复用于一切手写 CTest 项目（libfec 式 FEC/编解码库多为该形态）

## 红线

- 根级 ctest "No tests were found" 退出码 0 ≠ 通过（假绿）
- 不要为过门禁给上游打补丁把 enable_testing 挪到顶层（改变上游结构，适配目的无关）
- 计数不做 stdout 正则数数、不做算术修补（libbgcode 2026-09-20 preflight 教训）

## 度量

- 2026-10-02 libcorrect 0.0-git20260204 conan create（ohos-aarch64 双 profile）：4/4 passed，LastTest.log 口径，总耗时 121.74s
- CI 实证：PR #14383 构建 #68167 全绿（上游官方测试 + test_package + L0/L1 门禁全过）
