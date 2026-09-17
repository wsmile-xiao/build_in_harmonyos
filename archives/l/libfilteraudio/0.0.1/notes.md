# libfilteraudio 0.0.1 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 Makefile，无 configure / CMakeLists / meson）
- 编译日期: 2026-09-15
- 编译器: clang 15.0.4（`tools.build:compiler_executables:c`，来自 Conan profile）
- 目标: OpenHarmony / HarmonyOS PC aarch64（profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built

## 编译步骤

上游 Makefile 只需要 `CC`：`$(CC) $(CFLAGS) -fPIC -c` 编译、`$(CC) $(LDFLAGS) -shared` 链接、
`ar rcs` 打静态库，`install` 目标同时安装 `.so` 与 `.a`。

```sh
# 探索（设备原生，用于确认 aarch64 可编译）
make -j1 CC=clang
# 配方路径
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

配方里 `build()` 只传 `CC`（取自 `tools.build:compiler_executables`，R33；裸 `${CC}` 在
release worker 上为空，而 Makefile 默认的 `cc` 在 OHOS sysroot 里不存在），
`package()` 用 `make install DESTDIR=<pkg> PREFIX= LIBDIR=lib INCLUDEDIR=include`
落成 Conan 标准布局（`include/` + `lib/`），保留上游的软链链
`libfilteraudio.so -> libfilteraudio.so.0 -> libfilteraudio.so.0.0.0`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aarch64 上是否需要剥离 SSE2 源文件 | `aec/aec_core_sse2.c`、`aec/aec_rdft_sse2.c` 整个文件被 `#ifdef __SSE2__` 包裹，`WebRtc_GetCPUInfo(kSSE2)` 调用点在 `WEBRTC_ARCH_X86_FAMILY` 下 | 无需补丁：aarch64 上两个 TU 编译为空，落可移植 C 路径；设备原生 `make` 与 conan 构建均一次通过 |
| 2 | soname 与包版本不一致 | 上游 Makefile 仍写 `VERSION = 0.0.0`（v0.0.1 tag 没有跟着改），soname 由 VERSION 末段决定 = `libfilteraudio.so.0` | 不覆盖 VERSION：传 `VERSION=0.0.1` 会让 soname 变成 `.so.1`，属 ABI 误声明；保留上游 0.0.0，`.pc` 的 `Version` 用发布版本 0.0.1 |
| 3 | 安装出的 `filteraudio.pc` 指向构建目录 | 上游 install 规则用 `$(abspath $(PREFIX))` 重写 `prefix=`，`PREFIX` 为空时 abspath 得到构建目录，落进包内即死路径 | `package()` 重写 `.pc` 为可重定位写法 `prefix=${pcfiledir}/../..`（与 `abiword-plugin-*` 同款） |
| 4 | 上游无自动化测试 | Makefile 只有 `all`/`install`/`clean`，无 `check`/`test`；`test/` 下两个文件是交互式 PortAudio 演示程序，不参与 `make` 构建 | 用 `test_package` 消费者测试补断言（28 条），并在 `test_package/MANIFEST.yml` 写明清点证据 |
| 5 | 本地 CI（`ci/conan/build_and_test.sh`）预下载后 `conan create` 报 `NotADirectoryError: ... v0.0.1.tar.gz` | 该脚本的预下载步骤用正则扫描 **conandata.yml 全文（含注释）** 提取 URL，再用 `content.replace(url, "file://" + path)` 裸字符串替换。原注释里的 `# Source: https://github.com/irungentoo/filter_audio` 被当成源地址（下载到 `predl_cache/f6b7032a_filter_audio`，5040 B 的仓库页），而它是 tarball 地址的**前缀**，于是 tarball URL 被改写成 `file://…/f6b7032a_filter_audio/archive/refs/tags/v0.0.1.tar.gz`（父路径是普通文件） | 注释里不写带 scheme 的仓库根地址（写 `github.com/irungentoo/filter_audio`），并在注释中写明原因；`sources.url` 仍是官方 tarball 地址。改正后 W3 预下载得到干净的 `file://` tarball 路径 |

## 源码修改

无补丁（`patches: []`）。构建输入只有 `conanfile.py` / `conandata.yml` / `test_package/`。

## 依赖版本

无 Conan 依赖。链接的系统库：`-lm`、`-lpthread`（`package_info().system_libs`）。

## 验证结果

```sh
# 消费者测试（链路为安装后的 lib/libfilteraudio.a + include/filter_audio.h）
./test_libfilteraudio
# → 28 checks, 0 failed  (rc=0)

# ASan+UBSan 复跑（detect_leaks 在鸿蒙平台不支持，已关）
ASAN_OPTIONS=detect_leaks=0 ./test_asan
# → 28 checks, 0 failed；0 条 sanitizer 报告
```

上游测试清点：Makefile 目标仅 `all`/`install`/`clean`（`grep -nE '^[A-Za-z_.-]+:' Makefile`），
无任何测试框架注册，`other/speex_resampler.c` 的 `main()` 在 `#if 0` 内。故上游可运行自动化
用例 N = 0，本次实际运行 N′ = 0。

## 交付物

| 文件 | 说明 |
|------|------|
| `include/filter_audio.h` | 公开头文件 |
| `lib/libfilteraudio.a` | 静态库（默认 `shared=False`） |
| `lib/libfilteraudio.so.0.0.0` + `.so.0` / `.so` 软链 | 共享库（`-o shared=True`，soname `libfilteraudio.so.0`） |
| `lib/pkgconfig/filteraudio.pc` | 可重定位 pkg-config 元数据 |

## 注意事项

- `filter_audio()` / `pass_audio_output()` 的 `samples` 必须是 `fs/100` 的整数倍（10 ms 帧），
  否则返回 -1；`new_filter_audio()` 内部把除 16000 以外的采样率按 32000 处理，8k/48k 输入会被
  重采样，调用方仍按自己的采样率切帧。
- `cpp_info.system_libs = ["m", "pthread"]`：静态消费时必须带上，否则 `WebRtcSpl_*`/`speex_*`
  的数学与线程符号解析不到。
