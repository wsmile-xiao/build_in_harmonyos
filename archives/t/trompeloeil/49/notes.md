# trompeloeil 49 适配笔记

## 编译环境
- 构建系统: cmake（上游 `CMakeLists.txt`，header-only INTERFACE library；测试为独立自测程序）
- 编译日期: 2026-09-16
- 编译器: clang/clang++ 15.0.4（OHOS SDK LLVM，`aarch64-linux-ohos` 目标），libc++ 15
- 目标平台: HarmonyOS PC (OHOS) aarch64（conan profile: `ohos-aarch64` / 本机验证用 `ohos-aarch64-device`）
- 构建工具: cmake 4.4.3 / GNU Make 4.4.1 / Conan 2.29.1（OHOS 适配版）
- 状态: built
- 上游版本: tag `v49`（Conan 版本号 `49`），许可证 BSL-1.0

## 源码
- 官方源: `https://github.com/rollbear/trompeloeil/archive/refs/tags/v49.tar.gz`
- sha256: `2523571fb7920b2813cbc23b46e60294aba8ead7eba434bfec69c24408615593`（本机对上游 tarball 实测）
- 结构（v49 起拆分为多文件，但仍是 header-only）:
  - `include/trompeloeil.hpp`（伞头）+ `include/trompeloeil/{mock,lifetime,matcher,sequence,stream_tracer,coro,cpp11_shenanigans}.hpp` + `include/trompeloeil/matcher/*.hpp`
  - `include/{catch2,gtest,doctest,boost,criterion,crpcut,cxxtest,cantata}/trompeloeil.hpp`（各测试框架适配头）
  - `test/`: Catch2 v3 自测（`compiling_tests.cpp` + `_11`/`_14`，C++20 追加 `test_co_mock.cpp`），另有 `thread_terror.cpp`、`custom_recursive_mutex.cpp`
  - `compilation_errors/`: 68 个**必须编译失败**的负向用例 + `check_errors.sh` / `verify_compilation_error.sh`
- 补丁: **无**（`patches: {}`，未修改任何上游源码或测试用例）

## 适配要点

1. **header-only 配方**：`package_type = "header-library"`，`package_id()` clear，
   `package()` 复制 `include/**/*.hpp` 与 `LICENSE_1_0.txt`；`package_info()` 声明
   CMake 目标 `trompeloeil::trompeloeil`（与上游导出的目标名一致，便于 CMakeDeps 消费）。
2. **上游自测在 `build()` 内真实执行（R51）**：
   - C++14：`self_test` + `thread_terror` + `custom_recursive_mutex`
   - C++20：`self_test`（追加协程用例 `test_co_mock.cpp`）
   - 68 个负向编译用例：C++14 与 C++20 各执行一轮
3. **禁止构建期联网**：上游 `test/CMakeLists.txt` 找不到 Catch2 时会 `file(DOWNLOAD)`
   下载 `catch.hpp`。配方以 `tool_requires("catch2/3.8.1")` 提供 Catch2 v3，并把
   `self.dependencies.build["catch2"].package_folder` 传给 `-DCMAKE_PREFIX_PATH`。
   实测（未预置时）会生成 `build/test/catch/catch2/catch.hpp`（657,891 字节）；
   预置后不再生成任何下载文件，编译命令行含 `-DCATCH2_MAIN -DCATCH2_VERSION=3`。
4. **负向测试驱动器替换**：上游 `check_errors.sh` 用 GNU `parallel` 驱动
   `verify_compilation_error.sh`，OHOS 无 `parallel`。配方在 `build()` 里用 Python
   `ThreadPoolExecutor(2)` 逐用例调用**同一个** `verify_compilation_error.sh`
   （未改动上游脚本与用例），按输出行中的 `PASS`/`FAIL` 计数；判定语义与上游
   `FAILURES = cat $failfile | grep FAIL | wc -l` 等价。未命中两者即上游
   `// exception: <regex>` 规则排除的用例。
5. **TMPDIR 固定**：`verify_compilation_error.sh` 用 `mktemp`，OHOS `/tmp` 只读（E002），
   配方把 `TMPDIR` 指向 `${build_folder}/negative-tests-tmp`。
6. **编译器路径来源**：`self.conf["tools.build:compiler_executables"]`（R33），
   不依赖裸 shell 变量；cmake 配置显式传 `-DCMAKE_CXX_COMPILER`/`-DCMAKE_C_COMPILER`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 配置期从 GitHub 下载 `catch.hpp`（构建期联网） | `test/CMakeLists.txt` 在 `find_package(Catch2)` 失败后走 `file(DOWNLOAD)` 兜底 | `tool_requires catch2/3.8.1` + `-DCMAKE_PREFIX_PATH=<catch2 package folder>`；实测 `-DCATCH2_MAIN -DCATCH2_VERSION=3`，无下载 |
| 2 | `check_errors.sh` 无法运行 | 依赖 GNU `parallel`（OHOS 无此命令；toybox 无 `parallel`） | Python 线程池驱动同一 `verify_compilation_error.sh`，逐用例收集结果，失败即构建失败 |
| 3 | `mktemp` 在默认路径失败 | OHOS `/tmp` 只读（E002） | `TMPDIR` 指向构建目录（`negative-tests-tmp`） |
| 4 | CMake 提示 `System is unknown to cmake, create: Platform/HarmonyOS` | CMake 尚无 OHOS platform 模块（从编译器默认目标识别出 `HarmonyOS`） | 良性提示，`Threads` 探测仍命中 `pthread`，构建/运行不受影响 |
| 5 | GNU make `jobserver mkfifo ... Operation not permitted` 警告 | HMDFS 上 mkfifo 受限 | 非致命，`-j2` 并行构建正常完成 |

## 上游测试矩阵（真机实测，2026-09-16）

| 套件 | 标准 | 结果 |
|------|------|------|
| `self_test`（Catch2 v3） | C++14 | All tests passed (**1361 assertions / 604 test cases**)，exit 0 |
| `self_test`（含 `test_co_mock.cpp` 协程用例） | C++20 | All tests passed (**1394 assertions / 615 test cases**)，exit 0 |
| `thread_terror` | C++14 | exit 0（多线程调用/返回计数对称输出） |
| `custom_recursive_mutex` | C++14 | exit 0（`Pass! (the program compiled)`） |
| `compilation_errors/`（68 用例，expect-to-fail） | C++14 | 执行 50 PASS / 0 FAIL（18 个按上游 `// exception:` 规则排除） |
| `compilation_errors/`（68 用例） | C++20 | 执行 **68 PASS / 0 FAIL**（协程用例全部命中诊断正则） |
| test_package 消费者（Catch2） | C++14 | All tests passed (**5 assertions / 4 test cases**)，exit 0 |

> 负向用例的 `PASS` 语义 = 该翻译单元**按预期编译失败**且诊断文本匹配用例文件声明的
> `// pass:` 正则；`FAIL` = 编译成功或诊断不匹配。68 个用例在 OHOS clang 15/libc++ 15
> 上诊断文本**零漂移**（无需任何白名单或放宽）。

## 编译步骤（本地适配验证，可复现）

```bash
# 1) 自测（C++14）
CATCH2_PKG=$HOME/.conan2/p/<catch2 pkg>/p
clang++ --version   # 15.0.4
cmake -S .work -B build-cxx14 -DTROMPELOEIL_BUILD_TESTS=YES -DCXX_STANDARD=14 \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$CATCH2_PKG"
cmake --build build-cxx14 --target self_test thread_terror custom_recursive_mutex -j2
./build-cxx14/test/self_test              # 1361 assertions in 604 test cases
./build-cxx14/test/thread_terror          # exit 0
./build-cxx14/test/custom_recursive_mutex # Pass!

# 2) 自测（C++20，含协程）
cmake -S .work -B build-cxx20 -DTROMPELOEIL_BUILD_TESTS=YES -DCXX_STANDARD=20 \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$CATCH2_PKG"
cmake --build build-cxx20 --target self_test -j2
./build-cxx20/test/self_test              # 1394 assertions in 615 test cases

# 3) 负向编译测试（替代 parallel 的驱动；语义与上游一致）
cd .work/compilation_errors
export TMPDIR=<writable> CXX=<clang++ 路径>
CXXFLAGS="-std=c++14" sh -c 'ls *.cpp | xargs -P2 -n1 sh ../verify_compilation_error.sh'   # 50 PASS / 0 FAIL
CXXFLAGS="-std=c++20" sh -c 'ls *.cpp | xargs -P2 -n1 sh ../verify_compilation_error.sh'   # 68 PASS / 0 FAIL
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `include/trompeloeil.hpp` + `include/trompeloeil/**` | ~470 KB | 全部公共头（含 8 个测试框架适配头） |
| `lib/cmake/trompeloeil/`（消费端由 CMakeDeps 生成） | - | CMake 目标 `trompeloeil::trompeloeil` |

> header-only 包：`conan create` 产物为 `include/` + `licenses/`，无 `.a`/`.so`。

## 注意事项

- 本包不安装任何可执行文件（库类型，不需要 `commands.json`）。
- 编译上游自测体量较大（两个大 TU + 68 个负向编译），`conan create` 全量执行约 10 分钟；
  已实测 CI 默认 3600s 预算内完成。
- 若消费者自行编译上游 `test/`，务必预置 Catch2，否则 CMake 会尝试联网下载 `catch.hpp`。
---

**编译结束**: 2026-09-16 14:07
**最终状态**: built
