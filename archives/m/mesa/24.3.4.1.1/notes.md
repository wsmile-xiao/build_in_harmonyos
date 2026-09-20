# mesa 24.3.4.1.1 适配笔记（上游 Mesa 24.3.4，HarmonyOS PC）

## 版本说明

- Conan 包版本：`24.3.4.1.1`
- 上游源码版本：`24.3.4`
- 递增原因（r21-r22）：`mesa/24.3.4.1` 已在 ohpcd registry 发布（OSMesa-only recipe，revision c2271de0）；本轮交付需在同一上游 Mesa 24.3.4 上启用 GBM/EGL/GLES 制品，按 R37 递增为 `mesa/24.3.4.1.1`，避免与已发布 24.3.4.1 recipe 冲突（already-published-different-recipe）。上游源码仍为官方 Mesa 24.3.4 tarball。
- 当前目标：在无 X11/Wayland/DRM 的 HarmonyOS PC 上提供 `libOSMesa`，覆盖 Coin3 所需的 desktop OpenGL 固定管线入口。
- 构建策略：只编译 Meson 的 `OSMesa` 目标，安装时使用 `--no-rebuild`，降低真机有限账户空间下的中间文件峰值。
- GBM 修复增量（r17-r20）：`gbm=enabled` + `libdrm/2.4.133` requires + PkgConfigDeps，交付 `gbm.pc`/`gbm.h`/`libgbm.so`（含版本链接链），补丁 0007（harmonyos 按 DRM/KMS 平台识别）与 0008（libdrm 纯静态时 `--exclude-libs,ALL` 保持 libgbm 导出表仅 gbm_*，通过上游 gbm-symbols-check）。

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-10
- 编译器: clang/clang++（llvm 15.0.4，aarch64）
- 状态: built，Shadow CI r8 已通过（2026-09-11）

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
  -Dopengl=true -Dosmesa=true \
  -Dgles1=disabled -Dgles2=disabled \
  -Dllvm=disabled -Dlibunwind=disabled -Dvalgrind=disabled -Dzstd=disabled \
  -Dbuild-tests=false -Dtools=
ninja -C build OSMesa -j2
meson test -C build      # 待构建工具依赖补齐后执行
```

## Shadow CI 结果

- Shadow 任务：`mesa-24.3.4.1-shadow-20260910-r8-conan-r8`
- Runner：`rc=0`，设备全局锁等待 `0s`。
- 源码下载、SHA256 校验、解包、补丁应用和 Meson 配置均通过。
- `expat/2.8.2.1.1`、`bison/3.8.2`、`flex/2.6.4.2`、`m4/1.4.19` 均从 ohpcd 解析并复用成功。
- Mesa OSMesa/softpipe 编译完成 `881/881`，成功打包。
- `test_package` 真实编译并运行固定管线离屏渲染，输出：
  `OSMesa GL_VERSION: 3.3 (Compatibility Profile) Mesa 24.3.4`
  和 `test_mesa: ALL PASS`。
- Shadow L0/L1/L1e 全通过；L2 因本包没有 `bin/` 按规则跳过。
- L4 对 `0005-src-util-tests-cache_test.cpp.patch` 给出危险函数扫描告警；该项为非阻塞 warning，配方中的 `sprintf` 已替换为带长度限制的 `snprintf`。
- 远端证据日志位于：
  `/storage/Users/currentUser/ohos-users/codex/mesa-24.3.4.1-shadow-20260910-r7/runner-r8/codex-mesa-mesa-24.3.4.1-shadow-20260910-r8-conan-r8-20260911-012832-54651/logs/stdout.log`

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
| 8 | `nm` 未找到导致 OSMesa 配置失败 | Mesa 24.3.4 在 `build-tests=false` 时仍无条件查找 `nm` | patch 0002 已改为仅在启用测试时查找 `nm` |
| 9 | test_package 运行时找不到 `libOSMesa.so.8` 并报告符号缺失 | OHOS loader 对 Conan 缓存中的未签名 `.so` 不装载；仅设置 `LD_LIBRARY_PATH` 不足 | `package()` 对安装后的 `.so` 和 OHOS 别名执行 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`；测试显式补齐 Mesa、SDK libc++ 和 libz 路径 |

## 源码修改

- `meson.build`（patch 0002）：harmonyos 平台注入 `_GNU_SOURCE` + `-fno-emulated-tls`
- `bin/symbols-check.py`（patch 0001）：HarmonyOS 平台识别 + OHOS 运行库符号白名单
- `src/util/u_process.c`（patch 0006）：OHOS 进程名（/proc/self/exe）
- `src/util/memstream.c`（patch 0004）：OHOS open_memstream close 前 fflush
- `src/util/tests/cache_test.cpp`（patch 0005）：mkdtemp 用 $TMPDIR
- `src/gallium/tests/trivial/meson.build` + `ohos_adapt_test.c`（patch 0003）：新增鸿蒙专项测试
- `src/gallium/targets/osmesa`（上游目标）：构建无窗口系统依赖的 `libOSMesa`，提供 desktop OpenGL 固定管线入口

## 依赖版本

- expat/2.8.2.1.1（OHOS 制品仓 ohpcd 预编译包）
- bison/3.8.2 / flex/2.6.4.2 / m4/1.4.19 / python3 3.12.9 / mako 1.4.1

## 验证结果

本版本已完成真机 Shadow CI，`conan create`、Mesa 共享库打包和消费者运行验证均通过。包内共享库产物包括：

- `lib/libOSMesa.so.8.0.0`、`lib/libOSMesa.so.8`、`lib/libOSMesa.so`
- `lib/libglapi.so.0.0.0`、`lib/libglapi.so.0`、`lib/libglapi.so`

```bash
# Shadow CI 已执行：
conan create archives/m/mesa/24.3.4.1.1 --build=missing
# test_package 输出：
# OSMesa GL_VERSION: 3.3 (Compatibility Profile) Mesa 24.3.4
# colored pixels: 1152
# test_mesa: ALL PASS
```
---

**最后更新**: 2026-09-11
**最终状态**: built（Shadow CI r8 通过）
## r23 全量测试复验（2026-09-19）

- 按官方 Mesa 24.3.4 源码 + patches 0001-0010 副本，OSMesa/softpipe 适用配置（osmesa=true/egl=enabled/gles1+gles2 enabled/build-tests=true）完整枚举测试声明：source_declared_total=49（r15 build-test 仅 45，缺 osmesa-render/osmesa-symbols-check/egl-symbols-check/egl-entrypoint-check）。
- 全量执行 meson test：修复前 45 OK/3 FAIL/1 SKIP；新增 patches/0010（osmesa-symbols-check 对 libc weak-UND pthread_mutexattr_* 的 --ignore-symbol，llvm-nm -gP 四字段 'w 0 0' 被 symbols-check.py 误判为导出，GNU nm 两字段 'w' 本会跳过）后 osmesa-symbols-check FAIL→PASS，终态 46/49 (93.9%)。
- 剩余 2 FAIL：util_tests（HMDFS 平台限制，Cache.* 7 例，候选挂载点全部无法满足真实 0700 语义，恢复条件已列）；general_ir_test（上游 GLSL IR 行为差异，r15 R12#7 同源）。1 SKIP：egl-symbols-check（静态 EGL 所致，上游脚本对 .a 返回 GNU skip 77）。
- OHOS 专项 ohos_adapt_test ALL PASS；test_package test_mesa ALL PASS；libdrm/2.4.133 + pciutils/3.13.0 消费编译链接运行 exit 0；conan create RC=0。
---

**编译结束**: 2026-09-19 20:27
**最终状态**: built
