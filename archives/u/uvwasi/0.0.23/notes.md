# uvwasi 0.0.23 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-14
- 编译器: clang/clang++ (OHOS SDK, profile `ohos-aarch64`)
- 状态: published

## 源码
- 上游：https://github.com/nodejs/uvwasi
- 版本：0.0.23（tag `v0.0.23`，上游无 release tarball，用官方 GitHub archive）
- URL：`https://github.com/nodejs/uvwasi/archive/refs/tags/v0.0.23.tar.gz`
- sha256：`cdb148aac298883b51da887657deca910c7c02f35435e24f125cef536fe8d5e1`

## 依赖
- `libuv/1.52.1@ohpcd/stable`（已发布，W0 已确认 `conan list libuv/* -r=ohpcd` 命中）。

## 编译步骤

```bash
conan create archives/u/uvwasi/0.0.23 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方走标准 Conan CMake 流水线（`CMake` + `CMakeDeps`），不使用 zstd/glfw 那套
`ohos.toolchain.cmake` 自发现路线——本机构建容器无 OHOS SDK 的 ohos.toolchain.cmake，
该路线仅真机 CI 可用；标准 Conan toolchain 在容器与 CI 均可验证（参考 tesseract）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 默认 `find_package(LIBUV)` 找不到已发布的 libuv，回退 FetchContent 拉网失败 | 上游 CMakeLists 用自带 `cmake/FindLIBUV.cmake`（module 模式 find_library），与 Conan 的 `libuv` config 包名不匹配；CI/容器无外网 | 补丁 0001：把 find 改为 `find_package(libuv CONFIG REQUIRED)`，`LIBUV_LIBRARIES=libuv::libuv`，消费 Conan 已发布的 libuv |
| 2 | OHOS 下 `_GNU_SOURCE`/`_POSIX_C_SOURCE` 未定义 | conan 在 host==build 时不写 `CMAKE_SYSTEM_NAME`，cmake 退回宿主；CI worker `uname` 报 HarmonyOS，上游 `CMAKE_SYSTEM_NAME STREQUAL "Linux"` 不命中 | 补丁 0002：把 HarmonyOS 与 Linux 同等对待补上特性宏，消除容器(Linux)/CI(HarmonyOS) 分歧 |
| 3 | 共享库 libuvwasi.so 需 OHOS 代码签名，本机容器无 binary-sign-tool 无法本地验证 | OHOS 加载器校验 .so 代码签名 | 补丁 0003：仅构建静态库 uvwasi_a（移除 SHARED 目标并调整 install），规避签名；消费方静态链接 libuvwasi.a + 已签名的 libuv.so |

## 源码修改（补丁）

- `patches/0001-cmake-find-libuv-conan.patch`：CMakeLists 用 Conan libuv config 替代 FindLIBUV.cmake + FetchContent。
- `patches/0002-cmake-harmonyos-linux.patch`：CMakeLists 把 HarmonyOS 视同 Linux 设置特性宏。
- `patches/0003-cmake-static-only.patch`：CMakeLists 仅构建静态库（删 SHARED 目标，install 只装 uvwasi_a）。

三个补丁均为 `-p1`、git `a/ b/` 前缀、各自独立区域，顺序 apply 验证通过。

## 产物
- 静态库 `lib/libuvwasi.a`（目标 uvwasi_a，OUTPUT_NAME uvwasi）。
- 头文件 `include/uvwasi.h`、`wasi_serdes.h`、`wasi_types.h`。
- CMake 配置 `lib/cmake/uvwasi/`、pkg-config `lib/pkgconfig/uvwasi.pc`。

## 平台说明
- uvwasi 自身高度依赖 libuv 做 POSIX 抽象，未直接使用 glibc 专属 API（grep 源码
  `strchrnul/PATH_MAX/statx/getrandom/openat2` 等均无命中），OHOS/musl 可走通用 POSIX 路径。
- `clock_gettime` 在 musl/libc 内提供，无需显式 `-lrt`。
- test_package 静态链接 libuvwasi.a，运行期经 conanrun 解析已签名的 libuv.so。
