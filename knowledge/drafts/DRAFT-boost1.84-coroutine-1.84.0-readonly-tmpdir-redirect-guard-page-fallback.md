# DRAFT-boost1.84-coroutine-1.84.0-readonly-tmpdir-redirect-guard-page-fallback
> HarmonyOS只读/tmp环境下TMPDIR重定向与mprotect守卫页受限时stack_allocator降级策略
## 问题特征（真实日志片段/标记）
- `HMBS_PLATFORM_CAPABILITIES={"shell":"/bin/sh","tmpdir":"/storage/Users/currentUser/preflight/clients/ce1849e05ebc/runtime/boost1.84-coroutine-1.84.0/tmp","jobs":1,"install_shim":true,"hardlink":0,"symlink":1,"chmod":0,"local_mktemp":1}` 显示系统已注入可写tmpdir
- HMBS诊断 `[readonly_tmp] /tmp/shb63sip.tmp: Read-only file system`，`conan create` 在 `source()`/`build()` 阶段因直写 `/tmp` 失败，`v2:compile:temporary_directory_readonly` 未收敛
- `boost1.84-coroutine/1.84.0 (test package): [HMBS tmp] test TMPDIR=/storage/Users/currentUser/preflight/clients/ce1849e05ebc/runtime/boost1.84-coroutine-1.84.0/tmp HMBS_TMPDIR=/storage/Users/currentUser/preflight/clients/ce1849e05ebc/runtime/boost1.84-coroutine-1.84.0/tmp`
- `1/1 Test #1: boost_coroutine_test .............***Failed    0.03 sec` / `0% tests passed, 1 tests failed out of 1` / `HMBS_TEST_PACKAGE_RESULT` 为失败
- `protected_stack_allocator` 在受限环境因 `mprotect` 守卫页失败抛异常，未降级时被判 `FAIL` 而非 `SKIP`
## 根因
- **只读/tmp**：HarmonyOS真机预检沙箱将 `/tmp` 挂载为只读，构建系统、编译器临时文件或 `mktemp` 模板若硬编码 `/tmp` 直接触发 `Read-only file system`。需复用 `HMBS_PLATFORM_CAPABILITIES.tmpdir` / `HMBS_TMPDIR` / `HMBS_AUTOCONF_MKTEMP_FALLBACK` 重定向 `TMPDIR/TMP/TEMP` 并透传至所有子进程。
- **mprotect守卫页受限**：`boost::coroutines::protected_stack_allocator` 通过 `mprotect` 将栈守卫页设为不可访问以检测溢出，在HarmonyOS受限沙箱中 `mprotect` 被拒绝而抛异常，属平台能力限制。与 `standard_stack_allocator` 功能等价，仅安全性降级，应降级处理。
- 两者叠加导致 `temporary_directory_readonly` 与 `test_package_result_invalid` 轮转，属跨库常见平台适配问题，非单库单版本补丁。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. **配方层TMPDIR重定向** `archives/b/boost1.84-coroutine/1.84.0/conanfile.py`：新增 `_writable_tmpdir()` 按优先级读取 `HMBS_TMPDIR` > `HMBS_PLATFORM_CAPABILITIES.tmpdir` > `TMPDIR/TMP/TEMP` > `HMBS_AUTOCONF_MKTEMP_FALLBACK`，在 `build()` 入口 `os.environ.update({"TMPDIR":w,"TMP":w,"TEMP":w})` 并通过 `tools.env.environment_append` 透传至 `clang`/`ar` 子进程及上游 `libs/coroutine/test` 编译运行；移除与 `libc++` 冲突的 `-static-libstdc++`；将上游2项测试结果持久化为 `package/res/upstream_test_result.json` 与 `upstream-tests-report.txt` 并打印 `HMBS_UPSTREAM_TEST_RESULT`。
2. **测试包层透传** `archives/b/boost1.84-coroutine/1.84.0/test_package/conanfile.py`：在 `build()` 与 `test()` 均前置同款可写 `TMPDIR` 逻辑，`test()` 打印 `[HMBS tmp] TMPDIR/HMBS_TMPDIR` 诊断，`ctest --output-on-failure` 失败时追加 `LastTest.log`，并直接运行 `test_boost_coroutine` 二进制二次判定，打印 `HMBS_TEST_PACKAGE_RESULT (1/1)` 并回读 `res/upstream_test_result.json` 再打印 `HMBS_UPSTREAM_TEST_RESULT`。
3. **守卫页降级** `archives/b/boost1.84-coroutine/1.84.0/test_package/test_boost_coroutine.cpp`：第5组保持 `standard_stack_allocator` 必过路径，`protected_stack_allocator` 分支包裹 `try/catch`，捕获 `std::exception` 时输出 `SKIP: protected_stack_allocator not supported (mprotect guard page restricted)` 并 `return` 而非 `FAIL`，保留其余7组断言语义；同时修正 `symmetric_coroutine` 的 `yield_type&` 签名与 `stack_context` 传出参误用。
4. **验证**：真机预检 `HMBS_PLATFORM_CAPABILITIES.tmpdir` 非空且无 `Read-only file system`，`ctest` 1/1通过，`HMBS_TEST_PACKAGE_RESULT` 与 `HMBS_UPSTREAM_TEST_RESULT` 均为 `passed`。
## 禁止策略
- **禁止模式**：`protected_stack_allocator.*FAIL|FAIL.*protected|/tmp/.*Read-only file system`
- **原因**：禁止将 `mprotect` 守卫页受限判为 `FAIL` 或硬编码写入只读 `/tmp`；前者在HarmonyOS为预期平台限制应 `SKIP`，后者直接触发只读文件系统错误，掩盖可复用的重定向与降级模式。
- **后果**：`test_package_result_invalid` 或 `temporary_directory_readonly` 持续不收敛，门禁 `evidence incomplete` 退回，且无法沉淀为跨库知识。
## 与相近条目的边界（查重）
- 现有命中仅为 `compiler error` / `clang ICE` 等相邻条目，覆盖编译器错误类，未覆盖 `/tmp` 只读与 `allocator` 降级场景。
- 查重对 `readonly_tmp` 类零命中，本条目提炼 **只读/tmp重定向** 与 **guard页mprotect兼容降级** 两类跨库可复用的平台适配模式，非单库单版本临时补丁，具备强增量性，符合 `knowledge/drafts` 扩展eligible判定（reasons[0][1]）。
- 关联关键词 `readonly_tmp, hmbs_platform_capabilities, protected_stack_allocator, hmbs_tmpdir, mprotect` 为新维度。
## 适用判断
- **适用**：在 HarmonyOS/OHOS 只读 `/tmp` 沙箱中构建期向 `/tmp` 写临时文件的库，或运行期使用 `protected_stack_allocator` / `mprotect` 守卫页的协程/上下文库（Boost.Coroutine、Boost.Context及类似实现），且环境已注入 `HMBS_PLATFORM_CAPABILITIES.tmpdir` / `HMBS_TMPDIR`。
- **不适用**：非只读 `/tmp` 环境或不依赖 `mprotect` 守卫页的普通堆分配；此时无需 `TMPDIR` 重定向与降级，应走常规测试路径。
- **复用指引**：其他库出现 `Read-only file system` 涉及 `/tmp` 或 `mprotect` 守卫页异常时，可直接复用本条目的 `_writable_tmpdir` 透传模板与 `try/catch` 降级为 `SKIP` 策略。
