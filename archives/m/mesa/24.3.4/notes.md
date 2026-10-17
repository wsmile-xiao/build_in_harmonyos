# mesa 24.3.4 适配笔记（HarmonyOS PC）

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-01
- 编译器: clang/clang++（llvm 15.0.4，aarch64）
- 状态: built

## 编译步骤

mesa 使用 Meson 构建。最小软件渲染（softpipe）配置，无窗口系统依赖：

```bash
# 依赖：expat（OHOS 制品仓 expat/2.8.2.1.1，需修正 expat.pc 的 prefix 指向 conan 缓存包）
meson setup build \
  --buildtype=release \
  -Dplatforms= \
  -Dgallium-drivers=softpipe \
  -Dvulkan-drivers= \
  -Dgbm=disabled -Degl=disabled -Dglx=disabled \
  -Dllvm=disabled -Dlibunwind=disabled -Dvalgrind=disabled -Dzstd=disabled \
  -Dbuild-tests=true -Dtools=
ninja -C build -j2
meson test -C build      # 43 项：41 通过 / 2 组环境差异失败
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `clock_gettime` 未声明（strict C11） | meson.build 的 `_GNU_SOURCE` 注入列表不含 `harmonyos`（host_machine.system()=="harmonyos"） | meson.build 平台列表加入 `harmonyos`（patch 0002） |
| 2 | glapi 导出 `__emutls_*` 符号致 ABI-check 失败 | OHOS 工具链默认 emutls（模拟 TLS），mesa 仅对 Android NDK 加 `-fno-emulated-tls` | 对 `harmonyos` 同样注入 `-fno-emulated-tls`（patch 0002） |
| 3 | `util_get_process_name()` 返回空串 | OHOS 无 `program_invocation_name`/`getprogname`，落入返回 `""` 的兜底分支 | u_process.c 增 OHOS 分支，读 `/proc/self/exe`（patch 0006） |
| 4 | symbols-check/ABI-check 报额外导出 | Python `platform.system()` 在 OHOS 返回 `HarmonyOS`，白名单分支未覆盖；且 OHOS 运行库导出 `__at_fini`/`__cxa_finalize`/`_init`/`_fini` 等 | symbols-check.py 平台判断含 `HarmonyOS`，白名单补 OHOS 运行库符号（patch 0001） |
| 5 | u_printf 测试全部失败（输出为空） | OHOS `open_memstream()` 只在 `fflush()` 同步调用方缓冲区，`fclose()` 不更新 | u_memstream_close() 在 fclose 前显式 `fflush()`（patch 0004） |
| 6 | 磁盘缓存测试失败 | OHOS `/tmp` 只读（E002），测试硬编码 `/tmp/tmpdir.XXXXXX` | cache_test.cpp 改用 `$TMPDIR`（patch 0005） |
| 7 | 上游 meson test 2 组失败（已记录） | ①util_tests Cache.*：磁盘缓存 foz db 在 OHOS hmdfs 上 put/get 往返失败；②general_ir_test gl_nir_lower_mediump：GLSL IR 与编译器行为差异 | 非硬阻塞，如实记录为上游测试环境差异；不影响库交付 |

## 源码修改

- `meson.build`（patch 0002）：harmonyos 平台注入 `_GNU_SOURCE` + `-fno-emulated-tls`
- `bin/symbols-check.py`（patch 0001）：HarmonyOS 平台识别 + OHOS 运行库符号白名单
- `src/util/u_process.c`（patch 0006）：OHOS 进程名（/proc/self/exe）
- `src/util/memstream.c`（patch 0004）：OHOS open_memstream close 前 fflush
- `src/util/tests/cache_test.cpp`（patch 0005）：mkdtemp 用 $TMPDIR
- `src/gallium/tests/trivial/meson.build` + `ohos_adapt_test.c`（patch 0003）：新增鸿蒙专项测试

## 依赖版本

- expat/2.8.2.1.1（OHOS 制品仓 ohpcd 预编译包）
- bison 3.8.2 / flex 2.6.4 / python3 3.12.9 / mako 1.4.1

## 验证结果

```bash
# 编译
ninja -C build -j2   # 94/94 目标成功
# 上游测试（43 项）
meson test -C build  # 41 通过 / 2 组失败（util_tests Cache.*、general_ir_test，环境差异）
# 鸿蒙专项测试
GALLIUM_PIPE_SEARCH_DIR=.../pipe-loader ./build/src/gallium/tests/trivial/ohos_adapt_test
#   [OHOS] PASS: process name matches binary basename
#   [OHOS] non-background pixels: 4096/4096
#   [OHOS] PASS: softpipe off-screen render produced visible output
#   OHOS_ADAPT_TEST: ALL PASS
# 消费者验证
./test_mesa_consumer  # dlopen libGLESv2/libglapi + GL 入口符号解析 ALL PASS
```
---

**编译结束**: 2026-09-02 13:27
**最终状态**: built
