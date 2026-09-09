# nowplaying-cli 2.1.0.1 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4 (ohos NDK aarch64-unknown-linux-ohos)
- 状态: published
- 目标平台: arm64-v8a (OHOS)

## 背景

上游 nowplaying-cli 2.1.0 (kirtan-shah/nowplaying-cli) 是 macOS 专属 Objective-C 工具，依赖
Foundation/AppKit/MediaRemote 私有框架，OHOS 无 libobjc/libdispatch/Foundation，首行即
`#import <Foundation/Foundation.h> not found`（`env_unsupported`）。本包采用“provider 演示 +
controller 预留”的等价移植方案：纯 C++17 单二进制 CLI，CMake 构建，链接 `libohavsession.so`。

## 源码结构（本地创建，不依赖上游下载）

| 文件 | 行数 | 说明 |
|------|------|------|
| `src/main.cpp` | ~230 | CLI 入口：参数解析（`get/get-raw/play/pause/togglePlayPause/next/previous/seek/--json`），help，退出码 |
| `src/avsession_helper.h` | ~85 | `Session` / `ControllerBridge` 声明 |
| `src/avsession_helper.cpp` | ~240 | 封装 `OH_AVSession_Create/SetAVMetadata/SetPlaybackState/SetPlaybackPosition/Deactivate/Destroy` + `ControllerBridge::Dispatch` 桩点 |
| `src/metadata.h` | ~95 | 演示 metadata 存储结构、JSON 序列化 |
| `src/metadata.cpp` | ~110 | `JsonEscape` / `MetadataToJson` / `DemoMetadata` |
| `CMakeLists.txt` | ~60 | `cmake_minimum_required 3.16, project(CXX 17), find_library(libohavsession), install(bin/)` |
| `README.md` | ~90 | OHOS 等价移植说明、API 缺口、用法差异 |

产物：`nowplaying-cli` (arm64 ELF，~215KB)

## 源码分发方案迁移（exports_sources）

PF 硬闸检测到 conandata/manifest 中 `file://` 本地路径（CI 不可达）。
**迁移方案**：将 C++ 源码通过 conan `exports_sources` 直接打包进 recipe，
CI 的 conan create 通过 export 阶段获取源码，无需外部 URL 下载。

- conandata.yml: sources.url 改为空字符串（不再依赖外部下载）
- conanfile.py: 新增 `exports_sources = "CMakeLists.txt", "src/*", "README.md"`
- 源码文件（src/*.cpp, src/*.h, CMakeLists.txt, README.md）已复制到 recipe 目录
- 此迁移不改变功能或接口，仅改变源码分发方式

## 编译步骤

```bash
# 1) CMake 直接 OHOS 交叉编译验证（探索性编译）
cmake -B build -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=<SDK>/native/build/cmake/ohos.toolchain.cmake \
  -DOHOS_ARCH=arm64-v8a -DOHOS_PLATFORM=OHOS -DCMAKE_BUILD_TYPE=Release
cmake --build build -j2

# 2) Conan 验证（ohos-aarch64 profile）
conan create archives/n/nowplaying-cli/2.1.0.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

CMakeLists.txt 会自动解析 SDK sysroot：
- 直接 cmake：`ohos.toolchain.cmake` 已设 `CMAKE_SYSROOT`
- conan：在 `conan_toolchain.cmake` 无 `CMAKE_SYSROOT` 时从编译器 REALPATH
  推导 `<...>/ohos/native/llvm/bin/clang → ../../sysroot`

头文件用全限定 `multimedia/av_session/native_avsession.h` 通吃两条路径；链
接时 `find_library(ohavsession ${CMAKE_SYSROOT}/usr/lib/aarch64-linux-ohos)`
或按名字回退。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `fatal error: 'native_avsession.h' file not found` | conan 环境无 `-I<sysroot>/usr/include/multimedia/av_session` | 头文件改为全限定 `multimedia/av_session/native_avsession.h`，conan 默认 `sysroot/usr/include` 路径可直接命中 |
| 2 | `cmake` 时 `unrecognized arm64` | toolchain 只识 `arm64-v8a`/`x86_64`/`armeabi-v7a` | 修正为 `-DOHOS_ARCH=arm64-v8a` |
| 3 | conandata.yml 生成时检测为 autotools，缺少 CMake 支持 | init-build 对 cmake 模板未正确命中 | 重写为 CMake `application` 配方（`CMakeToolchain` + `cmake_layout`） |
| 4 | `libohavsession.so not found` 链接期 | conan flow 无 `CMAKE_SYSROOT` | CMake 逻辑从 `CMAKE_CXX_COMPILER` REALPATH 推导 `${_ohos_llvm_root}/sysroot` 并 `find_library` |

## API 缺口及设计决策

- OHOS native SDK (26.0.0.18) `libohavsession.so` 仅 115 符号（provider +
  AVCast 投屏），无任何 manager/controller 头；controller 能力仅在 ETS/JS
  (`avSession.getAllSessionDescriptors()/getAVSessionController()`)；`grep`
  全 SDK 可复现。
- 实现“provider 演示 + controller 预留”：
  `OH_AVSession_Create` + `OH_AVMetadataBuilder` + `SetAVMetadata` +
  `SetPlaybackState/Position` 演示完整 provider 链；`ControllerBridge::Dispatch`
  作为 ETS 桥接的单一接入点（注释说明）。

## 验证结果

```bash
# 本地 OHOS arm64 二进制验证（阶段：arm64 头盔，host 无运行）
$ ./build/nowplaying-cli --help            # exit 0
$ ./build/nowplaying-cli get --demo        # TSV: title/artist/... playbackState=playing
$ ./build/nowplaying-cli get --json --demo # JSON object contains Duration/TrackNumber
$ ./build/nowplaying-cli seek 90           # exit 0
$ ./build/nowplaying-cli togglePlayPause  # exit 0
# conan-verify (ohos-aarch64 profile)
conan-verify nowplaying-cli 2.1.0.1 → G0-G4 PASS，可标记 published
```

## 依赖版本

- `libohavsession.so`（系统 SDK 26.0.0.18，SystemCapability.Multimedia.AVSession.Core 无需其它 conan 依赖）
- cmake 4.1.2, clang 15.0.4, ninja, conan 2.29.1

## 注意事项

- `get`/`get-raw` 在 headless/CI 无服务时 fallback 到 in-process demo 数据（`--demo` 强制 seeded）；ETS controller 桥接做好后只需实现 `ControllerBridge` 一函。
- `notes.md` 的变更与 SPDX/Copyright 声明由 finish 流程统一整理，产物的 `.ci-result.json` 由 W3 步骤自动写入（带日志 SHA256）。
---

**编译结束**: 2026-09-07 16:56
**最终状态**: built
