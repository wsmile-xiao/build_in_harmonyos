# uhttpmock 0.11.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-24
- 编译器: clang/clang++（真机 /data/service/hnp 工具链，conan profile ci/conan/profiles/ohos-aarch64）
- 状态: built（首轮仅完成工作树，待 HMBS 真机预检回填实测数据）
- 申请人：zhangyuge147，队伍：龙骑士

## 背景

uhttpmock 是 Philip Withnall 维护的 HTTP(S) Web Service mock 库（libuhttpmock-1.0，
recording/playback of HTTP request-response traces），GNOME 生态（msgraph 等）的
测试依赖。上游 0.11.0 依赖 glib-2.0/gio-2.0 >= 2.38、libsoup-3.0 >= 3.1.2，
构建系统为 meson，与本仓已验证的 gssdp/libsoup3/gupnp 同栈，处理方案直接继承。

上游仓库：https://gitlab.freedesktop.org/pwithnall/uhttpmock
发布包：https://tecnocode.co.uk/downloads/uhttpmock/uhttpmock-0.11.0.tar.xz
（作者个人站点；真机/CI 网络连续三轮 ConnectTimeout，不可用）
现用源码：Debian/Ubuntu 官方归档 uhttpmock_0.11.0.orig.tar.bz2
（与上游 0.11.0 tag 归档逐字节相同），有序镜像列表见 conandata.yml：
TUNA 近端镜像首选 → archive.ubuntu.com 官方归档 → 上游 GitLab tag 归档保底，
sha256：27b591b34ed953100eee4589968f3978c2155c099b25c27a6bf0cffc7b148eef
（三方佐证：Gentoo Manifest DIST 大小 49657 + SHA512 完全匹配实测下载文件；
meson.build 确认 project version 0.11.0；单根目录 strip_root 安全）

## 编译步骤

```bash
conan create archives/u/uhttpmock/0.11.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

meson 配置（见 conanfile.py generate）：
-Dintrospection=false -Dvapi=disabled -Dgtk_doc=false -Ddefault_library=shared。
introspection/vapi/gtk_doc 均为上游可选的文档/绑定特性（GIR/vala/gtk-doc），
关闭不影响库本体。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | PkgConfigDeps 把已发布 libsoup3 配方的静态 glib 全家写进 generators/libsoup-3.0.pc 的 Libs 行 | libsoup3 配方 cpp_info.libs 内联了静态 glib（glib-2.0/gobject/gio/gmodule/gthread/ffi/intl） | generate() 对该 .pc 做 token 级剔除（保留 -lsoup-3.0 本体），Requires 行剔除 glib-2.0（gupnp 同款） |
| 2 | glib2 包内 .pc 前缀损坏（prefix=/）且 libffi 不可解析 | 上游安装前缀与包路径不一致；设备无系统 libffi | pc-fix 复制件修正 prefix 并清空 Libs/剔除 Requires 中的 libffi；PKG_CONFIG_PATH 优先使用复制件 |
| 3 | 共享库 strip / meson install 改写 .so 导致 OHOS loader 校验失败 | .codesign 哈希与内容绑定；meson install 清理 DT_RUNPATH 改写 .dynstr | tc.strip=None；package() 用 build 目录原始链接产物覆盖安装产物（libsoup3/gupnp 铁证） |
| 4 | CI worker 的 AR/AS/STRIP/NM/RANLIB 为 llvm-* 别名且不在 PATH | worker 环境导出值与实际工具位置脱节 | pop 掉环境变量，用 shutil.which 解析真实工具绝对路径注入 MesonToolchain |
| 5 | 真机 generate() 报 `Required build tools not in PATH: as`（2026-09-24 预检，compile 阶段） | 新版真机 PATH 无独立 `as`；uhttpmock 为纯 C 库，meson 默认用 C 编译器做汇编，无需独立汇编器 | `as` 改为可选（仅当 `as`/`llvm-as` 真实存在才 pin，否则保持 meson 默认）；`ar` 保留必需（含 `llvm-ar` 回退）；全部工具经 PATH + CC/CXX 驱动所在目录 + 已知 OHOS LLVM 目录文件探测，只 pin 真实存在的可执行文件，不把 clang 驱动映射为 `as` |
| 6 | 真机 `meson setup` 报 `/bin/sh: meson: inaccessible or not found`（exit 127，2026-09-24 预检，compile 阶段） | 配方沿用“CI 全局提供 meson”假设，build_requirements() 为空；HMBS 仅注入 cmake/make/ninja/python3，真机 PATH 无 meson | build_requirements() 新增 `tool_requires("meson/1.11.0")`（纯 Python，无 registry-ninja 依赖；registry ninja 仍不引入，沿用 profile 自带静态 ninja）；build() 内上游测试子进程改用显式 meson 路径解析（PATH 优先，其次 meson tool 包 bindir），找不到时如实发射 failed 标记而非猜测计数（fcft/3.3.3 同错先例，2026-09-09） |
| 7 | 真机 `meson setup` 报 `ERROR: Unknown compiler(s): [['/data/service/hnp/bin/clang']]`（`clang --version` ENOENT，2026-09-24 预检，tool_requires 生效后 compile 阶段） | profile 把 `tools.build:compiler_executables` 钉死在 `/data/service/hnp/bin/clang(++)`，该文件在此预检 worker 上缺失；MesonToolchain 把该原文烘焙进 native file，meson 探测编译器失败 | generate() 新增 `_resolve_compiler`（conf 存在性检查→CC/CXX→PATH→已知 LLVM 目录→`~/ohpc-ci-shadow/*/tools` 影子工具链）并在 `tc.generate()` 后用 `_patch_meson_native_compilers` 重写 native file 的 `c`/`cpp` 行（仅精确行替换，不动 c_ld/args）；`_sdk_bin_dirs` 同步覆盖影子目录以便 ar 等探测（bzrtp/5.3.105 的 CMake 工具链补丁 doctrine，转用于 meson native file；fftw3f 影子路径佐证） |
| 8 | 真机 `meson setup` 报 `Dependency lookup for glib-2.0 with method 'pkg-config' failed: Pkg-config for machine host machine not found`（2026-09-24 预检，编译器修复后 compile 阶段） | worker 无系统 pkg-config/pkgconf（HMBS 仅注入 cmake/make/ninja/python3）；配方未供给 pkg-config，meson 无法查询 glib-2.0 | build_requirements() 新增 `tool_requires("pkgconf/3.0.5")`（fcft/3.3.3 同错先例）；`_patch_meson_native_compilers` 兼把 native file 中裸 `pkgconfig = 'pkg-config'` pin 到解析到的绝对路径（PATH→pkgconf tool 包 bindir），找不到时保持原样由 meson 如实报错 → **本轮复检仍失败，确认无效：MesonToolchain 默认不写 pkgconfig 行，裸行正则从未命中，pin 从未生效（见 #9）** |
| 9 | #8 修复后复检仍报 `Pkg-config for machine host machine not found`（2026-09-24 预检，compile 阶段） | 上一周期根因假设（缺 tool_requires）已解决但实现路线错误：tool_requires 生效后仍找不到二进制，因为 pin 只做事后 `^pkgconfig = 'pkg-config'# uhttpmock 0.11.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-24
- 编译器: clang/clang++（真机 /data/service/hnp 工具链，conan profile ci/conan/profiles/ohos-aarch64）
- 状态: built（首轮仅完成工作树，待 HMBS 真机预检回填实测数据）
- 申请人：zhangyuge147，队伍：龙骑士

## 背景

uhttpmock 是 Philip Withnall 维护的 HTTP(S) Web Service mock 库（libuhttpmock-1.0，
recording/playback of HTTP request-response traces），GNOME 生态（msgraph 等）的
测试依赖。上游 0.11.0 依赖 glib-2.0/gio-2.0 >= 2.38、libsoup-3.0 >= 3.1.2，
构建系统为 meson，与本仓已验证的 gssdp/libsoup3/gupnp 同栈，处理方案直接继承。

上游仓库：https://gitlab.freedesktop.org/pwithnall/uhttpmock
发布包：https://tecnocode.co.uk/downloads/uhttpmock/uhttpmock-0.11.0.tar.xz
（作者个人站点；真机/CI 网络连续三轮 ConnectTimeout，不可用）
现用源码：Debian/Ubuntu 官方归档 uhttpmock_0.11.0.orig.tar.bz2
（与上游 0.11.0 tag 归档逐字节相同），有序镜像列表见 conandata.yml：
TUNA 近端镜像首选 → archive.ubuntu.com 官方归档 → 上游 GitLab tag 归档保底，
sha256：27b591b34ed953100eee4589968f3978c2155c099b25c27a6bf0cffc7b148eef
（三方佐证：Gentoo Manifest DIST 大小 49657 + SHA512 完全匹配实测下载文件；
meson.build 确认 project version 0.11.0；单根目录 strip_root 安全）

## 编译步骤

```bash
conan create archives/u/uhttpmock/0.11.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

meson 配置（见 conanfile.py generate）：
-Dintrospection=false -Dvapi=disabled -Dgtk_doc=false -Ddefault_library=shared。
introspection/vapi/gtk_doc 均为上游可选的文档/绑定特性（GIR/vala/gtk-doc），
关闭不影响库本体。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | PkgConfigDeps 把已发布 libsoup3 配方的静态 glib 全家写进 generators/libsoup-3.0.pc 的 Libs 行 | libsoup3 配方 cpp_info.libs 内联了静态 glib（glib-2.0/gobject/gio/gmodule/gthread/ffi/intl） | generate() 对该 .pc 做 token 级剔除（保留 -lsoup-3.0 本体），Requires 行剔除 glib-2.0（gupnp 同款） |
| 2 | glib2 包内 .pc 前缀损坏（prefix=/）且 libffi 不可解析 | 上游安装前缀与包路径不一致；设备无系统 libffi | pc-fix 复制件修正 prefix 并清空 Libs/剔除 Requires 中的 libffi；PKG_CONFIG_PATH 优先使用复制件 |
| 3 | 共享库 strip / meson install 改写 .so 导致 OHOS loader 校验失败 | .codesign 哈希与内容绑定；meson install 清理 DT_RUNPATH 改写 .dynstr | tc.strip=None；package() 用 build 目录原始链接产物覆盖安装产物（libsoup3/gupnp 铁证） |
| 4 | CI worker 的 AR/AS/STRIP/NM/RANLIB 为 llvm-* 别名且不在 PATH | worker 环境导出值与实际工具位置脱节 | pop 掉环境变量，用 shutil.which 解析真实工具绝对路径注入 MesonToolchain |
| 5 | 真机 generate() 报 `Required build tools not in PATH: as`（2026-09-24 预检，compile 阶段） | 新版真机 PATH 无独立 `as`；uhttpmock 为纯 C 库，meson 默认用 C 编译器做汇编，无需独立汇编器 | `as` 改为可选（仅当 `as`/`llvm-as` 真实存在才 pin，否则保持 meson 默认）；`ar` 保留必需（含 `llvm-ar` 回退）；全部工具经 PATH + CC/CXX 驱动所在目录 + 已知 OHOS LLVM 目录文件探测，只 pin 真实存在的可执行文件，不把 clang 驱动映射为 `as` |
| 6 | 真机 `meson setup` 报 `/bin/sh: meson: inaccessible or not found`（exit 127，2026-09-24 预检，compile 阶段） | 配方沿用“CI 全局提供 meson”假设，build_requirements() 为空；HMBS 仅注入 cmake/make/ninja/python3，真机 PATH 无 meson | build_requirements() 新增 `tool_requires("meson/1.11.0")`（纯 Python，无 registry-ninja 依赖；registry ninja 仍不引入，沿用 profile 自带静态 ninja）；build() 内上游测试子进程改用显式 meson 路径解析（PATH 优先，其次 meson tool 包 bindir），找不到时如实发射 failed 标记而非猜测计数（fcft/3.3.3 同错先例，2026-09-09） |
| 7 | 真机 `meson setup` 报 `ERROR: Unknown compiler(s): [['/data/service/hnp/bin/clang']]`（`clang --version` ENOENT，2026-09-24 预检，tool_requires 生效后 compile 阶段） | profile 把 `tools.build:compiler_executables` 钉死在 `/data/service/hnp/bin/clang(++)`，该文件在此预检 worker 上缺失；MesonToolchain 把该原文烘焙进 native file，meson 探测编译器失败 | generate() 新增 `_resolve_compiler`（conf 存在性检查→CC/CXX→PATH→已知 LLVM 目录→`~/ohpc-ci-shadow/*/tools` 影子工具链）并在 `tc.generate()` 后用 `_patch_meson_native_compilers` 重写 native file 的 `c`/`cpp` 行（仅精确行替换，不动 c_ld/args）；`_sdk_bin_dirs` 同步覆盖影子目录以便 ar 等探测（bzrtp/5.3.105 的 CMake 工具链补丁 doctrine，转用于 meson native file；fftw3f 影子路径佐证） |
 精确替换，而 MesonToolchain 默认不在 native file 写 pkgconfig 行 → 正则永不命中；且 generate() 内 shutil.which 看不到 tool bindir，包内只探 `bin/pkg-config|pkgconf` 单层 | 换路线：generate() 内先用增强 `_resolve_pkgconf`（PATH→tool 包 bindir 精确探→递归回退，同时兼容 `pkgconf`/`pkg-config` 双名）解析，解析到则预先 `tc.binaries["pkgconfig"]=绝对路径` + `PKG_CONFIG` 环境/buildenv 双导出；事后补丁改为“有行则替换、无行则向 [binaries] 插入”兜底；build() 开头再做一次 PKG_CONFIG 防御性重导出 |

## GObject 单副本说明（继承 gssdp/gupnp）

- GLib 系 .pc（pc-fix 复制件 + generators 生成件）的 Libs 全部为空或剔除了
  静态 glib token；静态 glib 不进入任何链接命令；
- libuhttpmock-1.0.so 对 g_type_*/g_object_* 保持 UND，运行时统一解析到
  libsoup-3.0.so 导出的唯一 gobject 副本；
- 本轮未预置 glib 最小补链归档（gupnp 为 g_uuid_string_random /
  g_zlib_compressor_new 所做的 guuid.c.o + gzlibcompressor.c.o 方案）：
  uhttpmock 直接调用的 gio API（GTask/GFile/GDataInputStream/GResolver 等）
  均为 libsoup 同样重度使用的主流 API，预期其符号已在 libsoup-3.0.so 导出
  表中。若真机链接报未解析符号，下一轮按真实报错提取对应上游翻译单元补链，
  不猜测、不预置。

## 上游测试

上游测试（libuhttpmock/tests/meson.build，uhm_tests 列表）：2 个测试程序。

| 程序 | 说明 |
|------|------|
| server | UhmServer 录制/回放/在线/离线/TLS/日志全流程测试 |
| resolver | UhmResolver 构造/A 记录查询/不存在域名/重置测试 |

取数口径：meson test 程序级（`meson test -C builddir` 注册项），
`upstream_test_total: 2`，`upstream_test_count_method: auto`
（单一 meson test 框架，从 tests/meson.build 的 uhm_tests 列表解析）。
build() 在 OHOS 设备原生执行 `meson test -v --no-rebuild`，逐行解析
`N/M <name> OK|FAIL` 结果行发射 HMBS_UPSTREAM_TEST_RESULT
（framework=meson），数字唯一来源为该解析；输出格式变化无法解析时如实
失败并给出 reason，不猜测计数。结果同时持久化到包内 res/hmbs_upstream.json，
供 test_package 在缓存命中轮次重发（bzrtp 同款模式）。
实测结果待 HMBS 真机预检回填。

## 依赖版本

- glib2/2.88.0（与 gupnp 1.6.10 / libsoup3 3.6.5-r1 同一修订，避免多修订共存）
- libsoup3/3.6.5-r1（ohpcd 已发布修订）
- zlib/1.3.1.1（override，PIC 变体；已发布 zlib/1.3.1 的 libz.a 非 -fPIC，
  链入共享 .so 会失败）

## 验证结果

首轮仅完成未提交工作树；编译与测试实测待 HMBS 真机预检回填：

```bash
# 待回填：conan create 日志中的 meson test 输出与 test_package 输出
```

## 注意事项

- 本库为纯 C 库（非深度适配类：无图形/多媒体/外设/系统底层平台分支），
  无需实质性 OHOS 平台适配代码；patches/ 为空，无 __OHOS__ 宏。
- test_package 用真实 API（UhmResolver + UhmServer），非空壳。
- Windows 工作区说明：上游 main 含 archives/l/libXext 与 archives/l/libxext
  两个仅大小写不同的目录，Windows 检出时仅保留一份，git status 显示
  archives/l/libxext/README.md 与 manifest.yaml 被修改——该差异为 Windows
  大小写文件系统产物，非本任务改动，Linux 真机不受影响。

## 本轮修复（2026-09-24 真机 meson test SIGABRT）

- 现象：`meson test` 2/2 FAIL，`g_type_register_static: assertion failed:
  (static_quark_type_flags)` + SIGABRT；旧解析器因 `1/2 uhttpmock:server FAIL
  0.23s ...` 尾部附加信息未匹配，误报 `executed 0 / unparsed`。
- 根因：generators/*.pc 清洗在 `tc.generate()` 之前执行，文件尚不存在，
  清洗静默 no-op；generators/glib-2.0.pc 保留全量静态 Libs，且其在
  PKG_CONFIG_PATH 中排在 pc-fix 之前，meson 优先命中，把第二份静态
  GObject 链进 libuhttpmock 与测试程序（与 gssdp 1.6.6 已验证教义相悖）。
- 修改：conanfile.py 新增 `_strip_glib_from_generated_pcs()` 并在
  `tc.generate()` 之后调用，遍历 generators/*.pc 做 token 级剔除
  （Libs/Libs.private 去静态 glib 全家，libsoup-3.0.pc 另去 Requires 中
  glib-2.0，保留 -lsoup-3.0）；解析器放宽为允许 verdict 后尾部信息、
  归一化 `suite:name` 前缀、正确统计 SKIP；_emit 增加 skipped 恒等式。
- 未跳过/删除任何上游测试；待 HMBS 真机预检验证。

## 本轮修复（2026-09-24 真机 server TLS 失败 + 计数断言）

- 进展：上轮 GObject 双副本已消除，server 前 7 个子项 ok，resolver 通过；
  残留 `server` FAIL 于 `test_server_properties_tls_certificate`
 （server.c:321）：`TLS support is not available` + `GDummyTlsBackend`。
- 根因有二：(1) OHOS glib 栈无 GIO TLS 模块（libsoup3 同栈 tls_check=false
  同源；glib-networking/2.90.0 绑定共享 glib/2.88.3，与本栈静态
  glib2/2.88.0 单副本教义冲突，无法作为缺依赖补齐）；(2) meson 失败项在
  进度列表与 `Summary of Failures` 各打印一次，旧解析器逐行计数致
  executed=3 > discovered=2，触发 `executed+skipped<=discovered` 断言，
  标记未发射。
- 修改：解析器按名去重（last verdict wins）；失败时按真实输出字符串
  发射 gaps（ohos_feature，count=失败数，含 server.c:321 与 GDummy 证据）；
  不删除/跳过任何上游测试。待 HMBS 真机预检验证。

## 本轮修复（2026-09-24 上游失败误判编译失败）

- 现状：标记已正确（discovered=2/executed=2/passed=1/failed=1+gaps），但
  build() 对 failed 直接 raise，导致 exit 6、stage=compile，package 与
  test_package 无法运行。
- 修改：失败时改为 warning 并继续打包（标记与 gaps 已持久化供门禁判定），
  不把测试缺口冒充编译失败，不吞结果。待 HMBS 真机预检验证。

## 本轮修复（2026-09-24 test_package CMAKE_C_COMPILER 缺失）

- Phenomenon: main package built (upstream marker 2/2/1/1+gaps emitted),
  test_package CMake configure aborts: `The CMAKE_C_COMPILER:
  /data/service/hnp/bin/clang` + `System is unknown to cmake`.
- Root cause: test_package used implicit `generators = CMakeDeps,
  CMakeToolchain, ...` so the profile-pinned
  `tools.build:compiler_executables` path was baked into
  conan_toolchain.cmake unchecked; that file is absent on this worker
  (same drift already fixed for the main meson native file, but the
  test_package domain was never patched).
- Change: test_package now uses explicit generate() (CMakeToolchain +
  CMakeDeps + VirtualRunEnv/BuildEnv) with compiler resolution
  conf-exists-check -> CC/CXX env -> PATH -> known OHOS LLVM dirs ->
  shadow layouts, cache_variables pin + conan_toolchain.cmake string
  replacement + CC/CXX buildenv export (zydis/4.1.1 pattern, adapted to
  keep the existing RPATH linker flags and marker logic). No test skipped.

## Test-package progress (2026-09-24: compiler fixed, header include failed)

- Previous test_package compiler patch verified effective: log shows
  `patched test_package compilers: c=.../.harmonybrew/bin/clang`,
  CMake configure passed, build started.
- New failure domain (different route from compiler fix): consumer compile
  `fatal error: 'libuhttpmock-1.0/uhttpmock/uhm.h' file not found`.
  Root cause is main-recipe `package_info.includedirs =
  ["include/libuhttpmock-1.0"]` doubling the `libuhttpmock-1.0/` prefix
  already present in the `#include` line. Fixed to `["include"]`,
  matching the upstream install layout
  `include/libuhttpmock-1.0/uhttpmock/uhm.h` and pkg-config subdir
  behaviour. No test skipped or stubbed.

## Fix 2026-09-24 test_package internal header

- Phenomenon: consumer include fixed by includedirs=[include], but new failure: uhm.h line 24 fatal error uhttpmock/uhm-message.h not found.
- Root cause: upstream layout needs two roots: consumer includes libuhttpmock-1.0/uhttpmock/uhm.h (needs -I include) while uhm.h itself includes uhttpmock/uhm-message.h (needs -I include/libuhttpmock-1.0). Single root satisfies only one side. Upstream pc Cflags carries the subdir.
- Change: package_info.includedirs=[include, include/libuhttpmock-1.0]. No test skipped or stubbed. Route changed from prefix-dedup to dual-root.
