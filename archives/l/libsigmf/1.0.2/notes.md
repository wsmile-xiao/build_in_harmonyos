# libsigmf 1.0.2 适配笔记

## 官方来源核验
- 官方仓库：https://github.com/deepsig/libsigmf（上游组织 DeepSig Inc.；sigmf/libsigmf 为其 fork 镜像）
- 标签：`v1.0.2`（tag SHA fc8f6e8346c4fc8a5440b97045de10271e0ab94e，GitHub tags API 实测）
- tarball：https://github.com/deepsig/libsigmf/archive/refs/tags/v1.0.2.tar.gz
- SHA-256：`dafa185c46e7295dac122a12a7b13763f67abdec7b707c3711060ccb4cfd78b2`（实测下载 68524 字节计算）
- 许可证：Apache-2.0（LICENSE + NOTICE）
- 构建系统：CMake（cmake_minimum_required 3.0，C++17，header-only INTERFACE 库 `libsigmf`）

## 项目结构（v1.0.2 tarball 实测，共 59 条目）
- 公共头：`src/`（sigmf.h、global.h、capture.h、annotation.h、collection.h、
  variadic_data_class.h、sigmf_helpers.h 等 9 个头文件）
- 预生成 flatbuffers 头 + `.fbs`：`sigmf_protocols/`（8 个 `*_generated.h`，下游无需 flatc 即可消费）
- 示例：`examples/`（5 个可执行：variadic_dataclass、multiple_namespaces、
  json_roundtrip、reading_sigmf_file、flatbuffer_patterns）
- `external/flatbuffers`、`external/json` 在发布 tarball 中为空目录（submodule 内容不打包），
  CMake 默认走 submodule 路径（`git submodule update --init`），CI/真机不可用，必须用系统依赖。

## 上游测试清点（R51）
- `examples/CMakeLists.txt` 注册 2 个 `add_test`：
  `simple_variadic_sigmf_to_json`、`simple_variadic_2ns_sigmf_to_json`。
- 顶层 `CMakeLists.txt` 未调用 `enable_testing()`，`ctest` 可能报告 0 注册；配方内 `ctest -N` 只作清点，
  两个已注册示例二进制在 `build()` 内直接运行（退出码 + `... passed` 输出双重判定）。
- README 原话：`Formal test code is still a WIP, examples provide some code coverage`。
- 结论：上游测试存在（2 项），`upstream_tests_exist: true`，不使用 `no_tests`。

## 依赖（W0）
- 唯一第三方依赖：nlohmann_json（上游偏好 3.7.3）、flatbuffers（上游要求 2.0.0 语法）。
- ohpcd 制品仓 in-tree 已有：nlohmann_json/3.12.0、flatbuffers/25.12.19（含 flatc，默认 `flatc=True`），
  配方直接引用这两个已发布版本，无需先发布依赖。
- 消费方式：`-DUSE_SYSTEM_JSON=ON -DUSE_SYSTEM_FLATBUFFERS=ON`；
  `find_package` 经 `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` 预载（ohos.toolchain 把
  `FIND_ROOT_PATH_MODE_PACKAGE` 设为 ONLY，命令行 `-D` 盖不住，沿用本仓库
  json-schema-validator/nlohmann_json 实证模式）；`flatc` 经依赖 `bindirs` 前置到 `PATH`。

## 编译步骤（真机由 HMBS 后台执行，本轮未在本机跑 conan）
1. `get` 解包 v1.0.2 tarball（strip_root）。
2. 自发现 `ohos.toolchain.cmake`，bare-cmake 配置（绕开 os=OHOS 下 CMakeToolchain 的
   `CMAKE_SYSTEM_NAME` 映射问题，沿用仓库既有模式）：
   `-DCMAKE_TOOLCHAIN_FILE=... -DOHOS_ARCH=arm64-v8a -DCMAKE_BUILD_TYPE=Release`
   `-DUSE_SYSTEM_JSON=ON -DUSE_SYSTEM_FLATBUFFERS=ON -DENABLE_EXAMPLES=ON`
   `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（上游 `cmake_minimum_required(VERSION 3.0)` 与 CMake 4.x 的兼容垫片）。
3. `cmake --build`（构建 flatc 代码生成 + 5 个示例），随后运行 2 个上游示例并输出
   `HMBS_UPSTREAM_TEST_RESULT` 标记。
4. `cmake --install`：头文件到 `include/sigmf/`、`.fbs` 到 `include/sigmf/fbs/`、
   CMake config 到 `lib/cmake/libsigmf`。
5. `test_package`：CMakeDeps + CMakeToolchain 消费者构建，运行 `test_libsigmf`
  （6 处显式运行时检查），输出 `HMBS_TEST_PACKAGE_RESULT` 标记。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 发布包无依赖源码 | GitHub tarball 不打包 submodule，external/* 为空 | 用系统依赖（USE_SYSTEM_*=ON），requires 引用制品仓版本 |
| 2 | `cmake_minimum_required(VERSION 3.0)` | CMake 4.x 移除了 <3.5 兼容 | `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（json-schema-validator 先例） |
| 3 | 顶层无 `enable_testing()` | 上游疏漏，ctest 可能 0 注册 | `ctest -N` 只清点；2 个二进制直接运行并判定退出码/输出 |
| 4 | 上游示例用 `assert()` 精确比对 | Release（NDEBUG）下 assert 为空操作，存在静默通过风险 | 如实披露；精确比对由 test_package 的显式 if 检查覆盖（不用 assert） |
| 5 | `find_package(Flatbuffers/nlohmann_json)` 在 OHOS 工具链下找不到包 | ohos.toolchain 以普通 set() 设 ONLY，命令行 cache 变量盖不住 | `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` 预载脚本同时追加 `CMAKE_PREFIX_PATH`（仓库既有模式） |
| 6 | `flatc` 命令找不到 | generate 步骤调裸 `flatc`，bare-cmake 不自动继承依赖 bindir | `build()` 内把依赖 `bindirs` 前置到 `PATH` |

## 源码修改
无（零补丁，`patches: {}`）。适配全部通过 CMake 选项与工具链配置完成。

## 依赖版本
- nlohmann_json/3.12.0（header-library，package_id 恒定）
- flatbuffers/25.12.19（flatc=True，FLATBUFFERS_BUILD_CPP17=ON，LOCALE_INDEPENDENT=OFF）

## 验证结果
- 本轮为首轮工作树准备（按任务要求不跑本地 conan、不 commit、不 push、不建 PR），
  真机 `conan create` + `test_package` + 上游测试由 HMBS 后台在本轮结束后统一执行；
  预检日志返回后按实际输出回填通过率并修复问题。
- 证伪预案：测试二进制输出必须含 `... passed` 行且退出码 0；参照文件（预生成头 8 个、
  tarball 59 条目）已在准备阶段计数确认非空；若真机出现空跑/静默跳过，按标记口径计 skipped 并补因。

## 注意事项
- header-only：`package_type="header-library"`，`package_id` 恒定，无 `shared`/`fPIC` 选项；
  `cpp_info` 无 libs（`bindirs=[] libdirs=[] libs=[]`），透传两个依赖。
- 非系统同名库，不涉及 R26 静态化；纯库无可执行产物，不需要 `commands.json`（R38）。
- 平台判断：本配方无 `settings.os` 分支，无 R32 风险；全程 C++17（`sigmf` 要求 `std::optional`）。
- Windows 工作树注记：上游 main 同时存在 `archives/l/libXext` 与 `archives/l/libxext`
 （仅大小写差异），Windows 不区分大小写导致 `git status` 恒有一处 M，与本任务无关，未触碰。

## 2026-09-17 Round4 native-build without NDK file (2nd strategy cycle)
- Why prior route failed: Rounds 1-3 all assumed cross-compile needing
  ohos.toolchain.cmake on disk (mirror list, wider globs + conan fallback,
  primary-only + os.walk). The Round3 log proves the assumption wrong: with
  the widest search the worker still reports user_toolchain=[] and no file
  under /data/service/hnp/ohos-sdk.org (which resolves to
  ohos-sdk_26.0.0.18/ohos/native/... per the profile LD_LIBRARY_PATH, yet
  glob Case A should have hit it). Per docs/ADAPTATION_GUIDE.md section 2
  the build is NATIVE (build==target==OHOS/aarch64, compiler
  /data/service/hnp/bin/clang from ci/conan/profiles/ohos-aarch64) -- no NDK
  sysroot or toolchain file is needed.
- New route (different implementation): deleted the entire manual
  _ohos_toolchain discovery, manual cmake command lines, FIND_ROOT preload
  hook, and bindir PATH hack. Follows the proven in-tree header-only CMake
  precedent jwt-cpp/0.7.1 (+ parallel-hashmap/2.0.0): CMakeDeps +
  CMakeToolchain with CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=
  aarch64 on OHOS, then plain CMake helper configure/build/install. flatc
  comes from the conanbuild env automatically. Upstream 2 example binaries
  are located by recursive search under build_folder (single- and
  multi-config layouts) with no /tmp writes (readonly_tmp guard).
- test_package generate() gets the same Linux masquerade (voro/0.4.6
  test_package precedent).
- Falsification: if next preflight still fails at configure, the log will
  show a compiler/flag error (not InvalidConfiguration about a missing NDK
  file), proving the fingerprint changed; if binaries are missing, the
  warning names exactly which one was not found.
- Postscript (Round5 verdict): this route reached cmake.configure() but the
  Linux masquerade broke the compiler check (see Round5 below); the
  masquerade is superseded, do not reuse it.

## 2026-09-17 Round5 plain toolchain + writable TMPDIR (same fingerprint 2nd fix)
- Previous result: Round4 removed the NDK search and reached
  cmake.configure(), but failed with "The CXX compiler identification is
  unknown" for CMAKE_CXX_COMPILER /data/service/hnp/bin/clang++.
- Why the masquerade was wrong: knowledge/DRAFT-nng-1.10.1 explicitly lists
  tc.variables["CMAKE_SYSTEM_NAME"]="Linux" as forbidden platform spoofing;
  for POSIX libs the stock-CMake "System is unknown to cmake" warning is
  non-blocking and the plain Conan toolchain (OHOS->HarmonyOS mapping, as
  designed in ci/conan/profiles/ohos-aarch64) builds fine. Forcing
  SYSTEM_NAME=Linux against the OHOS clang wrapper is what poisoned the
  compiler identification. Live preflight evidence outranks the older
  jwt-cpp/parallel-hashmap masquerade precedent.
- New route (different implementation, minimal): deleted the
  CMAKE_SYSTEM_NAME/CMAKE_SYSTEM_PROCESSOR overrides in both the main
  recipe and test_package; plain CMakeDeps + CMakeToolchain with only the
  project vars (POLICY_MINIMUM 3.5, USE_SYSTEM_*, ENABLE_EXAMPLES). Kept
  the recursive example-binary search and both HMBS markers unchanged.
- readonly_tmp (HMBS platform diagnosis): the worker /tmp is read-only and
  HMBS injects a writable per-task TMPDIR/TMP/TEMP; generate() now ensures
  the injected dir exists so compiler probes and CMake scratch files never
  fall back to /tmp. No test was skipped or deleted for this.
- Falsification: if the next preflight still fails compiler identification,
  the full CMakeError.log will show whether the probe used /tmp (then the
  TMPDIR fix was insufficient) or a flag/sysroot mismatch (then the issue
  is compiler flags, not platform identity).
- Postscript (Round6 verdict): plain toolchain ALSO failed at
  cmake.configure() with "System is unknown to cmake / Platform/HarmonyOS"
  plus the same broken compiler check. Three CMake routes exhausted
  (NDK search, Linux masquerade, plain toolchain); the failure is
  CMake-side compiler detection, not the compiler. Superseded by Round6.

## 2026-09-17 Round6 CMake-free build (same fingerprint 3rd fix, new strategy)
- Previous results: Round4 (Linux masquerade) and Round5 (plain toolchain)
  both died in cmake.configure() compiler detection for
  /data/service/hnp/bin/clang++; Round3 (NDK file search) never found the
  file on this worker. Common factor in all failures is CMake itself, so
  this round removes CMake from every compile step instead of tuning it.
- Decisive evidence: nymphrpc/v0.1.1 invokes the profile clang++ directly
  (no CMake) and is PASS on true-device CI, proving the compiler links and
  runs natively; upstream libsigmf is a pure INTERFACE library whose
  examples link nothing but headers (verified against upstream
  CMakeLists.txt v1.0.2: target_link_libraries(example... libsigmf) only).
- New implementation: build() regenerates the 8 flatbuffers headers with
  the Conan flatc using upstream's exact flags, direct-compiles the 2
  registered add_test example sources with the profile compiler
  (-std=c++17, src + generated + Conan json/flatbuffers includes) and runs
  them, asserting exit 0 plus a ... passed line (no silent pass). No
  NDEBUG is defined so assert() exact-JSON compares stay live -- stronger
  than upstream's own Release build. package() replicates upstream
  `cmake --install` layout via copy() (fbs to include/sigmf/fbs, pregen
  headers then flatc-built headers overwrite, src headers to
  include/sigmf). test_package likewise direct-compiles test_libsigmf.cpp
  (no CMake) and parses the CHECKS a/b line for the marker numbers.
- Test mouth unchanged: upstream discovered=2 (exactly the 2 registered
  add_test entries = full suite), consumer 6 explicit checks; same
  commands, same pass criteria, nothing skipped or deleted.
- Leftovers: test_package/CMakeLists.txt is now unused (kept to minimize
  diff; consumer build no longer uses CMake); software-level
  manifest.yaml build.system still says cmake (metadata only, sync after
  green).
- Falsification: if preflight fails, the log shows either flatc missing
  (ConanException names it), a direct compile error (full clang command
  line is echoed), or a binary exit/output mismatch (output is echoed
  before the verdict) -- each points at a distinct next fix, never back
  to CMake tuning.
- Postscript (Round7 verdict): Round6 reached the direct-compile step but
  died with "/bin/sh: /data/service/hnp/bin/clang++: inaccessible or not
  found" (Error 127) plus preflight.sh "can't create temporary file
  /tmp/*.tmp: Read-only file system". The hardcoded compiler path and the
  shell-string self.run() were the failure, not the flags. Superseded by
  Round7 below; do not reuse bare hardcoded compiler + shell-string compile.

## 2026-09-17 Round7 shell-free + compiler/tmpdir hardening (3rd strategy cycle)
- Why Round6 failed: Round6 assumed the profile compiler path
  /data/service/hnp/bin/clang++ is always executable and that mkdir-ing the
  injected TMPDIR is enough. The preflight log disproves both: the shell
  could not exec the hardcoded path (127 "inaccessible or not found" --
  same fingerprint as bwm/0.6.3 where the profile SHELL/CC pointed at
  absent HNP binaries), and /bin/sh itself hardcodes /tmp for temp files
  (preflight.sh[306] "can't create temporary file /tmp/*.tmp"), so any
  self.run() shell string can die before exec. mkdir without write-probe
  and without build_folder/tmp fallback is insufficient (coinor-vol
  precedent: $HOME/tmp may be unwritable; only mkstemp probe counts, R49
  forbids X_OK probing).
- New route (different implementation, no CMake return): keep the CMake-free
  direct-compile strategy but harden the host layer, adapted from
  bwm/0.6.3 (build-scope SHELL/CONFIG_SHELL/TMPDIR/CC/CXX override +
  isfile compiler fallback + inline exports, proven success x1) and
  myman/4.0.116 (write-probed TMPDIR pin + PATH fallback _cc). Adapted, not
  copied: this package has no configure script, so only the
  shell/tmpdir/compiler pattern is reused.
  Main recipe: added generate() saving a build-scope env script
  (libsigmf_hmos_fix) overriding SHELL/CONFIG_SHELL/TMPDIR/TMP/TEMP/CC/CXX;
  source()/build() pin a write-probed TMPDIR (HMBS_AUTOCONF_MKTEMP_FALLBACK
  path when real, then HMBS_TMPDIR/TMPDIR/TMP/TEMP/HMBS_INSTALL, mkstemp
  probe each, fallback build_folder/tmp); _resolve_compiler() keeps the
  profile value only when isfile, else PATH/SDK search (clang/clang++/cc,
  /storage/.../usr/local/bin, harmonybrew, HNP, LLVM sibling from
  LD_LIBRARY_PATH); _prepend_toolchain_path() puts the resolved dir on PATH;
  flatc + both example compiles + binary runs all go through shell-free
  subprocess arg lists with the pinned env (no /bin/sh /tmp temp files).
  test_package: same TMPDIR pin + compiler fallback + shell-free compile.
- Test scope unchanged: upstream discovered=2 (exactly the 2 registered
  add_test entries = full suite), consumer 6 explicit checks; same pass
  criteria (exit 0 + "... passed" / "CHECKS a/b + passed"), nothing skipped
  or deleted.
- Falsification: if preflight still fails, the log now distinguishes the
  layer: "no usable C++ compiler found" (with profile dump + PATH) means
  host has no clang at all; "flatc failed" names the .fbs file; "upstream
  compile failed" echoes the full argv without shell quoting; a binary
  exit/output mismatch echoes output before verdict. None of these can be
  confused with the old CMake compiler-detection fingerprint.
- Postscript: Round7 fixed the compile layer (upstream 2/2 passed on the
  next preflight); the remaining failure moved to test_package compile, see
  Round8 below.

## 2026-09-17 Round8 test_package Optional/string type fix
- Previous result: Round7 shell-free hardening worked -- the next preflight
  built the package and ran both upstream examples (HMBS_UPSTREAM_TEST_RESULT
  discovered=2 executed=2 passed=2). New failure is one layer up, in
  test_package build(): test_libsigmf.cpp:55 "no member named 'value_or' in
  'std::string'" for author.value_or(""). Different file and root cause from
  Round7 (host/toolchain vs test-source type error), so this is a new fix,
  not a repeat.
- Root cause: upstream flatbuffers split -- string fields (GlobalT.author /
  description, AnnotationT.description/generator, ...) are plain
  std::string, while numeric/bool fields (sample_rate/frequency/sample_count/
  mobile/gain, ...) are flatbuffers::Optional<T> (verified against upstream
  v1.0.2 sigmf_core_generated.h / sigmf_antenna_generated.h and the upstream
  example, which assigns author = "Nathan" directly). The consumer test
  wrongly assumed every field was optional and called .value_or() on a
  std::string. No assertion deleted, no test skipped: same 6 checks, same
  CHECKS a/b + passed marker contract.
- Fix: rewrote the 4 field checks by kind -- std::string fields use direct
  == comparison; Optional<T> fields use has_value() + operator* (present on
  all flatbuffers Optional, no value_or dependency). JSON key checks (3-4)
  and roundtrip structure (5-6) unchanged.
- Falsification: if preflight still fails in test_package, the log names the
  exact line/field again (each check is independent); a runtime CHECK FAIL
  line plus "test_libsigmf FAILED" exit 1 proves the harness catches real
  mismatches (no silent pass).

## 2026-09-17 Round9 cache-hit dual-channel upstream evidence
- Observed: preflight 2026-09-17T14:54 reports conan create through and
  test_package 6/6 passed, but verdict incomplete with
  "missing HMBS_UPSTREAM_TEST_RESULT". Log shows "libsigmf/1.0.2: Already
  installed!" so Conan skipped build() from cache; the sole marker emission
  lived in build(), hence no upstream evidence on this run. Prior round did
  emit discovered=2 executed=2 passed=2 when build() ran, so test logic is
  proven; the gap is channel placement, not test validity.
- Fix (adapted from cubelib experience 1, not copied): keep primary build()
  emission, add a genuine second channel in test_package. Vendored the 2
  upstream add_test sources verbatim (Apache-2.0 headers kept) as
  test_package/upstream_example_*.cpp; test_package build() compiles them
  fresh against the installed package headers (-std=c++17, no NDEBUG) and
  test() executes both, verdict exit 0 + "... passed" line, then emits
  HMBS_UPSTREAM_TEST_RESULT via self.output.info + print() dual channel plus
  upstream_results.json per-case file. Main build() also hardened to dual
  channel + exception fallback (failed marker on early error, never silent).
- Scope unchanged: upstream discovered=2 (exactly the 2 add_test entries =
  full suite), consumer 6 checks; nothing skipped or deleted. Cache-hit runs
  now produce live upstream evidence from real execution.
