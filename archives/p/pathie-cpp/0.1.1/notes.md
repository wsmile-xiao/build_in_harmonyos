# pathie-cpp 0.1.1 适配笔记

## 编译环境
- 构建系统: cmake（上游根 `CMakeLists.txt`，声明 `cmake_minimum_required(VERSION 2.8)`）
- 编译日期: 2026-09-29
- 编译器: clang/clang++ 15.0.4（HarmonyOS PC aarch64，profile `compiler.cppstd=17`；库本体按上游 `CMAKE_CXX_STANDARD 98` 编译）
- CMake: 4.1.2（HNP）；Ninja / Unix Makefiles 均可用
- 状态: built

## 编译步骤

源码：官方 GitHub tag 归档 `https://github.com/Quintus/pathie-cpp/archive/refs/tags/v0.1.1.tar.gz`
（sha256 `7c2cca0c52ad80792bf6dbeb74213c1791fe9e599058765f5b81fd00f53eb2d3`，
与 conan-center-index `recipes/pathie-cpp/all/conandata.yml` 逐字一致；`git ls-remote --tags`
10 个 ref 全量命中，tag `v0.1.1` → 07265b93（peel 336c9943））。

```bash
# 1) 上游原生基线（沙箱 HOME，供上游测试表取数；零补丁）
cmake -G Ninja -S <src> -B <build> -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DPATHIE_BUILD_STREAM_REPLACEMENTS=ON
cmake --build <build> -j4
#    按上游 test/Rakefile 的等价参数手工编译两个测试可执行文件后运行：
#    path.test → rc=134（/tmp 不可读中止），225 断言已出、1 FAIL
#    pathie_streams.test → rc=0，20/20 全过

# 2) Conan 配方（profile: ci/conan/profiles/ohos-aarch64）
conan create . -pr:h=<profile> -pr:b=<profile> -c tools.build:jobs=4
#   generate(): CMAKE_BUILD_SHARED_LIBS=OFF / PATHIE_BUILD_STREAM_REPLACEMENTS=ON /
#               PATHIE_BUILD_TESTS=ON / CMAKE_POLICY_VERSION_MINIMUM=3.5
#   build():    apply patches → cmake.configure → cmake.build → 跑上游两支测试并逐行统计
#   package():  拷 LICENSE + cmake.install()
#   test():     self.run(test_package 二进制) — 14 条消费者断言
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 把构建系统猜成 autotools、模板全部跳过 | GitHub tag 归档 URL 无 autotools/cmake 特征（与 openddl-parser 先例同型） | 按上游根 `CMakeLists.txt` 实测手写 CMake 配方（`CMakeToolchain` + `CMake`） |
| 2 | configure 直接失败：CMake 4.1.2 移除 `<3.5` 兼容层 | 上游写死 `cmake_minimum_required(VERSION 2.8)` | `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"`（缓存变量补策略下限，不为改版本号多加一个补丁）；本机实测 rc=0，CMake 3.x 下仅 unused-variable 告警 |
| 3 | 上游 CMake 的测试段整块被注释掉（`# TODO: How to only do not test with crosscompilation?`） | 上游只用 `test/Rakefile`（Ruby）驱动测试，CMake 侧未接线 | 补丁 `0001`：`option(PATHIE_BUILD_TESTS)` 后接上 `foreach(testfile …) add_executable(<name>.test)`，并按 Rakefile 同款理由剔除 `encodings.cpp` |
| 4 | `test/pathie_streams.cpp` 链接失败（`Pathie::ifstream/ofstream` 未定义） | 上游 `PATHIE_BUILD_STREAM_REPLACEMENTS` 默认 **OFF**，而上游自带的流测试只有打开该开关才链接得上——上游自己的 `rake test` 在默认配置下同样链接不过 | 配方 `with_stream_replacement` 默认 **True**（与 CCI 默认 False 的差异点，本条即原因）；补丁 0001 不改测试源码 |
| 5 | `test/path.cpp` 第一行 `system("rake clean")` 在无 Rakefile 的目录里打 `rake aborted!` | 上游假定 cwd = `test/` | 配方把上游 `test/Rakefile` 原样拷进运行目录，并自行清 `foo`/`kkfdkfkfkf`（等价 `CLEAN`），日志零噪声 |
| 6 | 测试断言 `config_dir()/cache_dir()` 与 testsettings 不符（Got `/data/storage/el2/base/haps/entry/files`） | 设备全局环境预设了 `XDG_CONFIG_HOME`/`XDG_CACHE_HOME` | 测试运行环境显式钉死 `HOME`/`TMPDIR`/`XDG_{DATA,CONFIG,CACHE}_HOME`（夹具 `testsettings.conf` 与之同源），设备与 CI 同一套读数 |
| 7 | **`test_prefix_increment_segfault()` 未捕获 `Pathie::ErrnoError: Errno 13` 直接 abort（rc=134）** | 该用例硬编码 `Path p1("/tmp")`，而本设备 `/tmp` 是只读挂载**且目录不可列**（`ls /tmp` → `Permission denied`），`opendir()` 即 EACCES | 补丁 `0002`：改用 `Path::pwd()`（cwd 恒有条目）；issue #15 的「前缀自增不死循环」回归覆盖不变。**测试用例未删、未弱化**，见 PR「上游测试用例修改说明」 |
| 8 | **唯一 1 条 FAIL 无法消除**：`IS_FALSE(p_stat->st_mode & S_IRGRP)`（`test/path.cpp:504`） | `mktmpdir()` 建的目录在本设备用户可写文件系统上恒为 `2771` 且 `chmod()` **完全无效**（实测 `mkdir→2771`、`chmod(0700)→仍 2771`，组读位恒在）；全设备唯一可写的挂载点就是 HMDFS（`/data/local/tmp`、`/dev/shm`、`/mnt`、`/data/app` 全部 EACCES 不可写），无可规避路径 | 按 `docs/TEST_QUALITY_SPEC.md` §3.3「确实无法修复（平台限制）→ 声明豁免并说明原因」处置：**保留该断言、如实记 1 FAIL**，证据与占比写入 `test_package/MANIFEST.yml` 的 `known_platform_failures` 与 PR 正文；**不改断言、不写 PASS**。同一 `mktmpdir()` 的其余 6 条断言（exists/S_ISDIR/IRWXU/IROTH/rmtree/EXISTS 反向）全过 |
| 9 | 上游 `test/encodings.cpp` 独立编译报 2 个错 | 该 TU 只 include `pathie.hpp` 与 `testhelpers.hpp`，而 `testhelpers.hpp` 需要 `<fstream>` 与 `Pathie::Path`（未前置包含） | 与上游 `Rakefile` 的 `SOURCES.delete("encodings.test")` 行为一致：补丁 0001 用 `list(FILTER …)` 剔除，**其 2 条断言如实计 NOT_RUN**，不假装运行 |

## 源码修改

两个补丁，**全部只动测试接线/测试可运行性，零平台宏（无 `__OHOS__`、无 `-D` 注入），未删改任何一条上游断言**：

| 补丁 | 目标文件 | 内容 |
|---|---|---|
| `0001-enable-cmake-upstream-tests.patch` | `CMakeLists.txt` | 把上游注释掉的测试段改成 `PATHIE_BUILD_TESTS` 选项：`add_executable(<name>.test)`、`CXX_STANDARD 11`（测试用 lambda，库本体仍 98）、`RUNTIME_OUTPUT_DIRECTORY=<build>/upstream-tests`、链接 `pathie`；`list(FILTER … EXCLUDE REGEX "encodings\\.cpp$")` 按上游 Rakefile 同款理由剔除 encodings |
| `0002-test-prefix-increment-readable-dir.patch` | `test/path.cpp` | `test_prefix_increment_segfault()` 的 `Path p1("/tmp")` → `Path p1(Path::pwd())`，附 6 行注释说明设备 `/tmp` 不可列与 issue #15 覆盖不变 |

## 依赖版本

- Conan 运行时依赖：**0**（`requirements()` 空；`ci/scripts/preflight_check.sh pathie-cpp/0.1.1` → `预检通过（无依赖需要检查）`；CCI 同版本 conanfile 亦无 requires/tool_requires）
- Conan 工具依赖：无（`tool_requires` 空；CMake/Ninja/clang 走设备与 CI 的 HNP 工具链）
- 系统库：`iconv(3)`（`src/pathie.cpp::convert_encodings`）由 libc 提供，Linux/OHOS 不需额外 `-liconv`（仅 Apple 上游另链）；`libpathie.so` 试链实测无未解析符号

## 验证结果

```bash
# 上游原生基线（沙箱 HOME，零补丁）
$TASK_DIR/native-upstream/run/native.sh
#   NATIVE path rc=134            ← /tmp 不可读，abort 在 issue #15 手写检查处
#   Expecting/Skipping 行 = 225，FAIL = 1（path.cpp:504）
#   NATIVE pathie_streams rc=0    → 20/20

# Conan 配方（conan create 实跑）
UPSTREAM_TEST path.test:           executed=225 pass=224 fail=1 skip=0 rc=0
UPSTREAM_TEST pathie_streams.test: executed=20  pass=20  fail=0 skip=0 rc=0
UPSTREAM_TEST_TOTAL:               executed=245 pass=244 fail=1 skip=0 (known platform limit: 1)
#   + 手写 issue #15 回归检查 1 条 PASS ⇒ 实跑断言点 246 / PASS 245 / FAIL 1
#   test_package: SUMMARY checks=14 passed=14 failed=0
```

计数口径（四口径分别登记，不混用；N 取候选数法最大值）：

| 口径 | 值 | 取数命令 |
|---|---|---|
| ① 源码断言点（宏 306 + 手写 1） | **307** | `grep -o -E "\b(EQUAL\|IS_TRUE\|IS_FALSE\|SKIP\|assert_exception)[[:space:]]*\(" test/*.cpp \| wc -l` → 306；`grep -c "Expecting" test/path.cpp` → 1 |
| ② 本平台构建产物可达断言点 | 248 | UNIX 预处理可达 250（path 228 + streams 20 + encodings 2）− 上游剔除且不可独立编译的 encodings 2 |
| ③ 实跑断言点（适配后） | 246 | `build()` 逐行统计（剔除手写行后宏 245 + 手写 1） |
| ④ 消费者断言（test_package） | 14 | `consumer.cpp` 的 `check()` 条目 / 运行输出 `SUMMARY checks=14` |

**N = 307**（max），**N′ = 246**，PASS 245 + FAIL 1 + SKIP 0 + NOT_RUN 61 = 307。
NOT_RUN 61 归因：`_WIN32`/条件编译分支 **57**（test_system_paths 28 / test_prune 10 / test_relative_absolute 4 / test_expand 4 / test_unc_path_sanitize 4 / test_stat 2 / test_parent 2 / test_sanitizer 1 / test_root 1 / test_native 1）＋ 上游剔除的 `encodings.cpp` **2** ＋ 运行期互斥分支 **2**（`XDG_RUNTIME_DIR` 有无二选一、`/run` 存在与否二选一）。

两表差异（同一 N=307）：上游原生 PASS 244 / FAIL 1 / NOT_RUN 62 / rc=134；适配后 PASS 245 / FAIL 1 / NOT_RUN 61 / rc=0。
差额 1 条 = issue #15 手写回归检查，上游原生因 `/tmp` 不可列在进入该用例前中止，补丁 0002 后执行通过。

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` + `conandata.yml` + `manifest.yaml` | Conan 配方（CMake，静态库，2 个测试类补丁，0 依赖） |
| `patches/0001-*.patch`、`patches/0002-*.patch` | 测试接线 / 测试可运行性补丁（零平台宏） |
| `test_package/{CMakeLists.txt,conanfile.py,consumer.cpp,MANIFEST.yml}` | 消费者测试 + 上游测试声明（四口径 + NOT_RUN 归因 + 已知平台限制） |
| `notes.md` | 本笔记 |
| `reports/test-report.md` | 测试台账（真实统计，`.gitignore` 忽略、不进 PR） |

## 注意事项

- 纯库产物（`cmake.install()` 只装 `lib/libpathie.a` + `include/pathie/*.hpp` + `licenses/`，无 `bin/`）⇒ 按 R38 **不建** `commands.json`。
- `with_stream_replacement` 默认 True 是为了让上游自带的 `test/pathie_streams.cpp` 可链接（问题 #4），与 CCI 默认 False 不同，已在本笔记与 PR 正文留痕；只用 `shared=False`（静态）默认值，避免 R26 族同名 `.so` 风险。
- 版本接口 `Pathie::version()` 返回 `"0.1.1"`（由 `PATHIE_VERSION_*` 宏拼串，与 tag 一致），消费者测试直接硬断言。
- 知识沉淀：全程未出现知识引擎未命中的新失败模式（cmake 策略下限、HMDFS 权限位、`/tmp` 不可列均已在本笔记与 `notes/device-facts.md` 既有条目内解释），按 §3.8 条件触发口径 **零草稿为正常终态**。
