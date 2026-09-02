# quill 13.0.0 适配笔记

## 编译环境
- 构建系统: cmake（quill 为 CMake INTERFACE header-only 库）
- 编译日期: 2026-09-02
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: published（conan-verify 全门禁通过，等待 CI release 发布）

## 编译步骤

```bash
# 源码（官方 tag v13.0.0, sha256=88b4a1542125577a4d51cf444c51e34d63618c422ba6a4fa9bd23894b49d696b）
curl -sSL -o quill-13.0.0.tar.gz https://github.com/odygrd/quill/archive/refs/tags/v13.0.0.tar.gz

# 探索编译（本机 OHOS aarch64）
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$PREFIX \
      -DQUILL_BUILD_TESTS=ON
cmake --build build -j4
ctest --test-dir build -j4      # 419/419 通过（0 failed）

# Conan 配方验证（ohos-aarch64 profile）
python3 scripts/ohc-run.py conan-init quill 13.0.0
python3 scripts/ohc-run.py conan-verify quill 13.0.0   # G0-G4 + L2/L4/L5 全 PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | BackendWorkerLock 锁测试 5 项失败（duplicate_lock_throws 等） | OHOS /tmp 只读，open("/tmp/QuillBackendLock<pid>") 返回 EROFS → fd=-1 → 静默跳过锁检查 | include/quill/backend/BackendWorkerLock.h：锁文件路径改为 $TMPDIR（未设置时回退 /tmp），锁功能在 OHOS 真实生效 |
| 2 | console_sink_stderr/stdout_multiple_formats、json_console_logging、multiple_sinks_same_logger 失败 | test/misc/DocTestExtensions.cpp 的 CapturedStream 硬编码 /tmp/captured_stream.XXXXXX，mkstemp 失败 | DocTestExtensions.cpp：模板路径用 $TMPDIR 解析（Android 分支保留 /data/local/tmp） |
| 3 | coloured_console_applies_before_write_before_newline_handling 失败 | TestConsoleSink 用 std::tmpfile()，内部写 /tmp 失败 → has_file()==false | test/unit_tests/ConsoleSinkTest.cpp：改用 mkstemp($TMPDIR)+fdopen，析构时清理 |
| 4 | init-build 默认按 autotools 生成配方 | quill 是 CMake 库，非 autotools | conanfile.py 重写为 CMakeToolchain + package_type=header-library + QUILL_ENABLE_INSTALL=ON |
| 5 | LOG_INFO/Backend::flush API 误用（消费者测试首版编译失败） | quill 13 LOG_* 宏直接展开调用（无 quill:: 前缀），Backend 无 flush() 公开 API | 对照 examples/console_logging.cpp 与 integration tests 修正 test.cpp/test_ohos.cpp |

## 源码修改（OHOS /tmp 只读适配，refresh-patch 固化）

- include/quill/backend/BackendWorkerLock.h — 锁文件路径 $TMPDIR-aware
- test/misc/DocTestExtensions.cpp — 捕获流 mkstemp 模板 $TMPDIR-aware
- test/unit_tests/ConsoleSinkTest.cpp — TestConsoleSink 临时文件改 mkstemp($TMPDIR)
- test/unit_tests/BackendWorkerLockTest.cpp / BackendUtilitiesTest.cpp — 锁路径断言与库一致

## 依赖版本

- 无外部 Conan 依赖：quill 内嵌 bundled fmt；仅需系统 Threads（pthread）
- 编译器：clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)

## 验证结果

```bash
# 上游全量测试（CTest 419 项）
ctest --test-dir build -j4
# 100% tests passed, 0 tests failed out of 419

# test_package 消费者测试（实质调用 quill API 全链路）
./test_quill        # quill logging pipeline executed OK
# HarmonyOS 专项测试（TMPDIR 日志写入验证，本次适配核心点）
./test_quill_ohos   # PASS - log written to $TMPDIR/quill_ohos_test.log
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake header-only 配方（package_type=header-library） |
| conandata.yml | 官方源 URL + sha256 |
| test_package/test.cpp | 实质 C++ 消费者测试（Backend/Frontend/LogMacros 全链路） |
| test_package/test_ohos.cpp | HarmonyOS 专项测试（$TMPDIR 日志写入验证） |
| patches/ | OHOS /tmp 只读适配补丁 |

## 注意事项

- OHOS 平台 /tmp 为只读（Read-only file system），凡硬编码 /tmp 的上游路径都需 $TMPDIR 适配；本机 TMPDIR=/storage/Users/currentUser/tmp
- quill 13.0.0 为 header-only，无 .so/.a 产物；命令行为空库，无需 commands.json（R38）
- PR 前缀：【依赖项】（task_type=依赖项，供其他库消费）
---

**编译结束**: 2026-09-02 13:45
**最终状态**: published
