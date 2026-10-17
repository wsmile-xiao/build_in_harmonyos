# DRAFT-odiff-4.5.0-zig-ohos-libc-probe-incomplete-sysroot-global-bypass

> Zig 0.16 在 OHOS native 目标编译 C 依赖时宿主 libc 探测注入不完整 sysroot（bits/alltypes.h 缺失），用 -Dtarget=aarch64-linux-musl 或 vendor 完整 musl 头全局绕过；test_server spawn 受限需 access→statFile

## 问题特征（真实日志片段/标记）

真机 compile 阶段失败，C 依赖全部报缺 `bits/alltypes.h`：


/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/string.h:23:10: error: 'bits/alltypes.h' file not found
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/stdint.h:20:10: error: 'bits/alltypes.h' file not found
error: 32 compilation errors
failed command: .../zig-real build-lib ... deps/imgz/deps/zstd/deps/zstd/lib/common/zstd_common.c ...
Build Summary: 17/26 steps succeeded (3 failed)
install transitive failure


各 C 依赖独立报错数：jpeg-turbo 155、zlib 15、zstd 32。另见 test_package/evidence 阶段 server 端到端用例计数矛盾标记：


HMBS_UPSTREAM_TEST_RESULT={...discovered 48, executed 40, passed 40, failed 0, skipped 8...}


build runner 偶发 `failed to spawn ... build: AccessDenied`（包装器自恢复，非根因）。

## 根因

1. **Zig 0.16 OHOS native 目标 libc 探测注入不完整 sysroot**：zig/0.16.0.1 以 `native(.{})` 目标编译 C 依赖时，宿主 libc 探测无条件注入 OHOS SDK sysroot include（`--zig-lib-dir=<pkg>/bin/lib/` 佐证），其 `usr/include/stdlib.h`/`stdint.h` 依赖 musl `bits/alltypes.h`，而该 sysroot 不含此头。此注入与 CC/CXX/CFLAGS/CPATH 环境无关——`os.environ.pop` 清环境、`env=None` 跳 conanbuild.sh、CPATH 前置均无效（zig 0.16 探测行为已不同于 flow-control 验证过的 0.15.2）。
2. **module.addIncludePath 只作用到库自身模块**：odiff 的 `build.zig` 注入 `deps/ohos-shim` 只覆盖自身模块；imgz 经 `Imgz.addToModule` 在 `src/formats/*.zig` 以独立 `b.addLibrary` compile step 构建各 C 库，不继承父模块 include path，仍从 sysroot 解析而缺 `bits/*`。
3. **test_server 端到端用例在 OHOS spawn 受限**：`std.Io.Dir.cwd().access()`（新 std.Io API→faccessat）在 OHOS 对 `zig-out/bin/odiff` 报错、spawn 子进程有签名要求，8 个 server 用例走上游 `SkipZigTest` 判跳过，静默弃用；且替换为返回非 void 的 `statFile` 后需 `_ =` 丢弃成功值（否则 `error: value of type 'Io.File.Stat' ignored`）。

## 修复方案（rec）

**方案（rec_priority 1，全局 musl target 绕过）**：
1. `conanfile.py` 的 `build()` 中，OHOS 下让 `zig build` 与 `zig build test-all` 一律加 `-Dtarget=aarch64-linux-musl`，使 zig 全程用自带完整 musl 头、绕开 sysroot 探测，全局覆盖所有模块（含独立 C compile step）。宿主同 arch/os，`is_cross_compiling` 仍为 false，上游用例照常执行。此前的 `module.addIncludePath(ohos-shim)` 显式 `-I` 前置（文件级）可作同 worker 已验证的过渡，但须覆盖每个独立 C step。
2. `test_server.zig`（conandata patch `0001-*.patch`）的 9 处存在性探测由 `access()` 改为 `std.Io.Dir.cwd().statFile(io, path, .{})`（std.Io API、fstatat 家族，OHOS 支持），成功值在语句位置加 `_ =` 显式丢弃（catch 块以 `return`/`return error.SkipZigTest` 结束为 noreturn），使 8 个 server 用例真正执行。
3. 主 `zig build` 后、`test-all` 前对 `zig-out/bin/odiff` 先 `chmod` + `_sign_elf` 预签名，保证 server 用例 spawn 到可直接运行的 odiff。
4. 上游测试标记须诚实上报：passed==执行数、skipped==未执行数、恒等式 `passed+failed==executed`、`executed+skipped==discovered` 成立，`skipped>0` 且配 `ohos_feature` gaps 时 `status=incomplete`（不得标 passed）。注意 Zig 0.16 测试汇总输出为 `All N tests passed`（非 `N/N tests passed`），解析须匹配实际格式。

## 禁止策略

- 禁止静默吞掉跳过：`skipped=8` 却报 `discovered/executed/passed=40`、全标 passed → rule4 判『上游测试不足 100%，必须提供 gaps』或『passed 状态与上游结果矛盾』。
- 禁止只做环境级修复（清 CC/CXX/CFLAGS、`env=None`、CPATH）：对 Zig 0.16 探测通道不生效，仅重复失败。
- 禁止退回已弃用的 `std.fs.*`：应留在 `std.Io.Dir.cwd()` 下用 OHOS 可用的 statFile 家族。
- 禁止把 `self.settings` 门控逻辑放 `source()`（Conan 2 禁止访问），须移到 `build()`。

## 与相近条目的边界（查重）

- **flow-control/arptables（zig 0.15.2 清 CC 即可）**：相邻但不同——本条目为 Zig 0.16 探测行为改变，清环境与 `env=None` 均无效，须 `-Dtarget` 或文件级 vendor 头。
- **上游测试计数 / readonly_tmpdir / demo 提升为回归套件（ccrtp）**：相邻但不同——本条目聚焦 zig sysroot 头缺失与 access→statFile 的平台差异，不涉及 demo 改造或 tmpdir 模板。
- 此前无条目覆盖『Zig sysroot 头缺失全局绕过 + access→statFile 修复』，增量成立。

## 适用判断

适用于：Zig 0.16（及以上同类探测行为）在 OHOS native 目标编译、以独立 compile step 内联 C 依赖库的三方库，以及上游测试用 access 探测可执行文件存在性或 spawn 子进程的场景。若不能改 target，回退 vendor 完整 musl 头（文件级 `-I` 前置，须覆盖所有独立 C step）。
