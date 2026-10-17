# dd-opentracing-cpp 1.3.7 适配笔记

## 官方来源核验
- 官方仓库：https://github.com/DataDog/dd-opentracing-cpp
- 标签：`v1.3.7`（Release v1.3.7，2023-06-02，上游最新稳定版）
- tarball：https://github.com/DataDog/dd-opentracing-cpp/archive/refs/tags/v1.3.7.tar.gz
- SHA-256：`8d39c6b23f941a2d11571daaccc04e69539a3fcbcc50a631837560d5861a7b96`（与 conan-center-index 同一归档条目一致）
- 许可证：Apache-2.0
- 构建系统：CMake（cmake_minimum_required 3.13，C++14）
- 上游状态备注：Datadog 已声明本库 deprecated，建议新项目用 dd-trace-cpp；但 v1.3.7 仍是可用的稳定版本，适配本身不受影响。

## 项目结构
- 库源码：`src/*.cpp`，公共头：`include/datadog/`（安装保留该目录）
- 产物目标：`dd_opentracing`（shared，SOVERSION 0）/`dd_opentracing-static`（static，OUTPUT_NAME 相同）
- 上游默认 `scripts/install_dependencies.sh` 编译私有的 `deps/` 树（opentracing 1.6.0 / curl / msgpack），配方未采用该路径
- 上游测试：`test/` 下 13 个 ctest 可执行文件，基于 `3rd_party` 内 vendored Catch2，无外部测试框架依赖
- `3rd_party` 内同时 vendored 了 nlohmann/json 与 CLI11，库主体不需要外部 `nlohmann_json` 包

## 依赖（W0）
- `opentracing-cpp/1.6.0`（版本与上游 install_dependencies.sh 默认一致；公共头透传，需 transitive_headers/libs）
  - **阻塞**：本仓库 `archives/` 内尚无 opentracing-cpp 适配，制品仓是否已发布需真机 `conan download` 实证；
    若缺失，须先按拓扑顺序适配发布 opentracing-cpp 1.6.0，本包配方无需改动（引用名已按 conan-center 惯例固定）。
- `libcurl/8.5.0`（仓库内 coeurl 等已消费的版本）
- `msgpack-cxx/7.0.0`（仓库内 autobahn-cpp 已消费的版本；conan-center 原要求 6.1.0，7.0.0 同为 header-only，API 兼容）
- `zlib/1.3.1.1`（与 libcurl/8.5.0 的 `requires("zlib/1.3.1.1")` 对齐，避免图冲突）
- 不依赖 `nlohmann_json`：上游用 vendored 头，公共头也不暴露它。

## 配方设计
- 以 conan-center `dd-opentracing-cpp/all` 配方为基线，差异：
  1. `find_package` 目标名按 OHOS 制品仓实际修正：`msgpack-cxx`（conan-center 写 `msgpack` + 变量模式，不适用于本站包）、`ZLIB`（本站 `zlib/1.3.1.1` 提供 `ZLIB::ZLIB`）；
  2. 去掉 `patch_type` 之外的 sanitizers 逻辑：顶层 `add_sanitizers` 调用随补丁删除，`test/` 树的调用由 `generate()` 写入的
     `ohos-sanitizers-shim.cmake`（no-op `add_sanitizers`，经 `CMAKE_PROJECT_INCLUDE` 注入）兼容，避免对上游测试文件打空白敏感补丁；
  3. `BUILD_TESTING=ON` 常开，`build()` 内真实执行 `ctest --output-on-failure --timeout 120`，从输出解析
     `HMBS_UPSTREAM_TEST_RESULT`（discovered/executed/passed/failed 全部来自 ctest 汇总行，失败则抛错中断打包）；
  4. `BUILD_TESTING=ON` 会连带强制 `BUILD_SHARED=ON`，`package()` 按 `shared` 选项裁掉另一族产物（静态包删除 `libdd_opentracing.so*` 含符号链接）；
  5. `CMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容 CMake ≥ 4（与站内 opentracing-cpp 配方同法）。
- `package_info()`：`libs=["dd_opentracing"]`，按选项下发 `DD_OPENTRACING_SHARED/STATIC`，
  `cmake_file_name=dd-opentracing-cpp`，`requires` 链覆盖四个直接依赖。

## 上游测试清单（13 个，test/CMakeLists.txt）
agent_writer / opentracing / propagation / sample / span_buffer / span / tag_propagation /
tracer_factory / tracer_options / tracer / limiter / logger / glob（各 1 个 ctest 用例，Catch2 断言数待真机输出回填）。
集成测试（`test/integration/`，需 wiremock/msgpack-cli/真实 Agent）不属于 `ctest` 默认套件，未接入。

## test_package 设计
- `test_dd_opentracing.cpp`：10 项真实 API 检查（makeTracer 非空 → StartSpan 非空 → SetTag →
  流式 Inject/Extract 往返 → getOptions/toJSON → Finish），无 Agent 网络依赖（agent 指向 127.0.0.1 且不调用 Close 刷盘）；
   exit 码与 `DD_TEST_SUMMARY passed=N total=M` 行共同决定 `HMBS_TEST_PACKAGE_RESULT`（conanfile 解析该行，缺失/不等即判失败）。

## 待真机回填（本轮未提交工作树）
- `conan create` 实测（含 13 项上游 ctest 真实通过数、test_package 10 项检查输出）
- PR 正文「上游测试用例通过率」「新增测试用例通过率」
- `opentracing-cpp/1.6.0` 在制品仓的可消费性结论

## BLOCKER-2026-09-11 preflight dependency gap (working-tree note only)
- Result: failed at compile/graph phase. Evidence: ERROR Package 'opentracing-cpp/1.6.0' not resolved in remotes, required by dd-opentracing-cpp/1.3.7.
- Root cause: no archives entry and no SUMMARY entry for opentracing-cpp; CI L0i R36 would report unpublished_deps too. Reference opentracing-cpp/1.6.0 matches upstream install_dependencies.sh default and conan-center; recipe needs no change.
- Other deps look consumable: libcurl/8.5.0, msgpack-cxx/7.0.0, zlib/1.3.1.1 all have in-repo consumers; preflight only complained about opentracing.
- readonly_tmp diagnostic is preflight.sh /tmp noise; grep confirms no /tmp hardcode in this package, all paths use build_folder. No change made for it.
- No vendoring/bundling workaround: public header includes opentracing/tracer.h, bundling would collide with future opentracing package and break single-PR rule; no stubs, no test reduction.
- Next per W0/R36 topology: adapt and publish opentracing-cpp 1.6.0 first, then re-run this package conan create (13 upstream ctest + 10 test_package checks). Recipe/patch/test_package left uncommitted pending re-verify.

## STRATEGY-2026-09-12 vendor opentracing privately (second attempt, different from BLOCKER round)
- Same fingerprint failed again, so per policy a different strategy is used: vendor opentracing-cpp 1.6.0 privately instead of waiting for a standalone package.
- conandata.yml gains opentracing_sources (upstream v1.6.0 tarball, sha256 5b170042da4d1c4c231df6594da120875429d5231e9baa5179822ee8d1054ac3 from conan-center-index); CI mirror fallback still applies to the github.com URL, checksum untouched.
- source() downloads it to a sibling opentracing-src dir; build() compiles shared+static with the Conan toolchain into build_folder/opentracing-prefix (BUILD_MOCKTRACER/DYNAMIC_LOADING/TESTING/LINTING off, PIC on, jobs=1) and generate() puts that prefix on CMAKE_PREFIX_PATH.
- Patch fixed to the real exported targets OpenTracing::opentracing (shared/tests) and OpenTracing::opentracing-static (static lib); there is no OpenTracing::OpenTracing target.
- package() merges the private prefix include/lib into this package and ships LICENSE-opentracing-cpp; package_info libs gain opentracing plus OPENTRACING_STATIC define for static consumers; test_package drops its opentracing-cpp requires and links only dd-opentracing-cpp::dd_opentracing, with a self.run() re-execution for the L0d gate.
- Revert to a plain self.requires() once a standalone opentracing-cpp package is published.

## FIX-2026-09-12 ctest LD_LIBRARY_PATH (uncommitted, pending preflight)
- Evidence: upstream_test failed 13/13, every case `Error loading shared library libcurl.so`, `Error loading shared library opentracing-prefix/lib/libopentracing.so`, plus `Error relocating ../libdd_opentracing.so: curl_* symbol not found`; binaries never executed, so no test numbers to falsify yet.
- Root cause: test binaries link shared deps (Conan libcurl, vendored libopentracing, just-built libdd_opentracing.so) but OHOS loader has no RPATH to those dirs; `_run_upstream_tests` ran ctest with inherited env and no LD_LIBRARY_PATH (same pattern as ezstream 1.0.2 make-check 14/14 FAIL).
- Change (minimal, no test deletion/skip): added `_runtime_libdirs(ctest_dir)` collecting Conan dep libdirs + ot-prefix lib/lib64 + libdd_opentracing.so dirs + ctest dirs, `_subprocess_env(ctest_dir)` now exports LD_LIBRARY_PATH, `_run_upstream_tests` passes ctest_dir and logs the value; suite still parses real ctest output and raises on any failure.
## FIX-2026-09-12 readonly_tmp + ctest cwd (uncommitted, pending preflight)
- Evidence: preflight failed at compile with `preflight.sh[306]: can't create temporary file /tmp/*.tmp: Read-only file system`, then `cmake --build ... agent_writer.cpp.obj` followed by `Connection closed`; recipe grep shows no `/tmp` hardcode (all paths already under build_folder).
- Root cause (recipe side): vendored-opentracing `subprocess.run` and ctest/test-binary runs inherited env without an explicit writable TMPDIR guarantee, so compiler/test temp files could fall back to read-only /tmp; additionally `_run_upstream_tests` used `cwd=self.build_folder` while cmake_layout builds out-of-source (`build/Release`), which would discover 0 tests.
- Change (minimal, no test deletion): added `_effective_tmpdir`/`_subprocess_env` helpers (prefer HMBS-injected TMPDIR/TMP/TEMP, fallback `build_folder/hmbs-tmp`) and pass that env to vendored configure/build/install, to ctest, and to the test_package binary run; `_find_cmake`/ctest now prefer `HMBS_CMAKE` sibling first; ctest cwd now resolves to the dir containing `CTestTestfile.cmake` (`build/Release` first, then glob fallback).
- Falsification note: numbers still come only from real `ctest --output-on-failure` output; parse failure still raises, no skips added.

## FIX-2026-09-13 link vendored opentracing STATIC (uncommitted, pending preflight)
- Evidence: after the LD_LIBRARY_PATH round, libcurl errors are gone but all 13 ctest cases still fail with `Error loading shared library opentracing-prefix/lib/libopentracing.so: (needed by ../libdd_opentracing.so)`. The NEEDED entry contains a slash, so the loader treats it as a path and ignores LD_LIBRARY_PATH.
- Root cause: vendored shared lib link recorded path-form DT_NEEDED on the unknown HarmonyOS CMake platform; LD_LIBRARY_PATH (which fixed libcurl) cannot fix slash-containing NEEDED entries, and the packaged .so would carry the same bogus NEEDED.
- Change (different strategy, no test deletion/skip): vendored build is now static-only (BUILD_SHARED_LIBS=OFF, PIC on, stale .so self-healed); DATADOG_LINK_LIBRARIES links OpenTracing::opentracing-static so libdd_opentracing.so embeds opentracing and has no runtime dep on libopentracing.so. LD_LIBRARY_PATH handling for libcurl/just-built libs is kept. Suite still runs the real 13 ctest cases and raises on any failure.

## FIX-2026-09-13 TmpFile honors TMPDIR (uncommitted, pending preflight)
- Evidence: 12/13 pass; only tracer_factory_test fails at test/tracer_factory_test.cpp:633 with `unable to open temporary file for writing: /tmp/tmpnam_jCGkBK`. TmpFile uses std::tmpnam() which hardcodes /tmp (ignores TMPDIR), and /tmp is read-only on the device, so ofstream open fails. Setting TMPDIR in the ctest env cannot fix tmpnam.
- Change (different strategy, test-only, no assertion deletion): new conandata patch_type test `patches/0001-tmpfile-tmpdir.patch` relocates only the directory portion of the tmpnam result to harness-injected TMPDIR/TMP/TEMP; the temp file is still really created, written with real content, consumed by the DD_SPAN_SAMPLING_RULES_FILE sections, and removed in ~TmpFile. Applied via apply_conandata_patches at build() start.

## FIX-2026-09-12 upstream evidence dual-emit + cache-penetrating re-emit (uncommitted, pending preflight)
- Evidence: 2026-09-11 preflight incomplete at evidence stage: `DD_TEST_SUMMARY passed=10 total=10` present but gate reports missing HMBS_UPSTREAM_TEST_RESULT (discovered 0/executed 0). build() only used bare print() without flush/output.info, so the marker was lost in conan output capture; additionally a cached package binary skips build() entirely, leaving no upstream marker in that run.
- Root cause: single-channel emit (print only) + no persistence for cache-hit rounds. Same pattern solved by ayatana-ido 0.10.4-v2 (persist res/hmbs_upstream.json, re-emit from test_package) and numen 0.7 (print flush + output.info dual emit).
- Change (no test deletion/skip, numbers still only from real ctest): build() now dual-emits (print flush + self.output.info) and persists build_folder/hmbs_upstream.json, staged to package res/hmbs_upstream.json; test_package dual-emits its own marker and re-emits the persisted upstream JSON every run. Falsification unchanged: parse failure still raises, consumer DD_TEST_SUMMARY mismatch still fails.
