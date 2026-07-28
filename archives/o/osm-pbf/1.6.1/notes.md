# osm-pbf 1.6.1 适配笔记

## 目标

对齐 Homebrew [`osm-pbf`](https://formulae.brew.sh/formula/osm-pbf) 1.6.1（revision 6），上游 [OSM-binary v1.6.1](https://github.com/openstreetmap/OSM-binary/releases/tag/v1.6.1)。

## 环境

| 项 | 值 |
|----|-----|
| SDK | OpenHarmony 6.1.0.31（`/opt/ohos-sdk-6.1`） |
| 编译器 | OHOS Clang 15.0.4（`aarch64-unknown-linux-ohos-clang`） |
| 构建宿主 | Linux x86_64 Docker（容器 `oh_compile` / `665e6075…`） |
| CMake | SDK 自带 3.28.2 |

## 依赖（cmd-pkgs 预编译，R18）

| 包 | 版本 | 状态 |
|----|------|------|
| zlib | 1.3.1 | 已用 |
| abseil-cpp | 20260107.1 | 已用 |
| protobuf | 34.1 | 已用（Homebrew 为 35.1；34.1 可编译通过） |

宿主 codegen：`protoc-34.1-linux-x86_64.zip`（与目标 protobuf 主版本一致）。

## 构建命令（已验证）

```bash
export OHOS_SDK=/opt/ohos-sdk-6.1
export PREFIX=/root/ohos-deps   # 解压后的 cmd-pkgs 前缀
# 用宿主 protoc 覆盖 deps 前缀中的 aarch64 protoc
cp /opt/protoc-host/bin/protoc $PREFIX/bin/protoc

cmake -S . -B build \
  -DCMAKE_TOOLCHAIN_FILE=$OHOS_SDK/native/build/cmake/ohos.toolchain.cmake \
  -DOHOS_ARCH=arm64-v8a \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH=$PREFIX \
  -DCMAKE_CXX_STANDARD=17 \
  -Dprotobuf_MODULE_COMPATIBLE=ON \
  -DProtobuf_PROTOC_EXECUTABLE=/opt/protoc-host/bin/protoc \
  -DCMAKE_FIND_ROOT_PATH="$PREFIX;$OHOS_SDK/native/sysroot" \
  -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER
cmake --build build -j$(nproc)
cmake --install build --prefix /opt/osm-pbf-1.6.1
```

## 产物

- `lib/libosmpbf.a`
- `lib/libosmpbf.so*`（SOVERSION 1 / VERSION 1.5.0，与上游 project 版本一致）
- `include/osmpbf/{osmpbf.h,fileformat.pb.h,osmformat.pb.h}`
- `bin/osmpbf-outline`（NEEDED: `libc++_shared.so`, `libc.so`；protobuf/zlib/osmpbf 已静态链入可执行文件）
- `share/man/man1/osmpbf-outline.1`
- 预编译包：`packaging/osm-pbf-1.6.1-ohos-aarch64.tar.gz`（约 2.3MB）

ELF：`ARM aarch64`，interpreter `/lib/ld-musl-aarch64.so.1`。

## 问题与处理

| # | 问题 | 处理 |
|---|------|------|
| 1 | OHOS `protoc` 经 qemu 执行 SIGILL/segfault | 使用宿主 x86_64 protoc 34.1，并覆盖 deps 前缀中的 protoc |
| 2 | `Protobuf_PROTOC_EXECUTABLE` 被 protobuf Config 覆盖 | 直接替换 `$PREFIX/bin/protoc*` |
| 3 | 本机 qemu-aarch64 无法跑任何 OHOS musl 二进制（含 hello） | 交叉环境仅做编译/链接验证；真机再跑 `osmpbf-outline sample.pbf` |

## Homebrew 对照

| Homebrew | 本适配 |
|----------|--------|
| cmake + abseil + protobuf | 同；protobuf 用已发布 34.1 |
| `osmpbf-outline` + sample.pbf 测 OSMHeader | 配方安装 sample.pbf；真机验证 |
| Linux 额外 zlib-ng-compat | 用 zlib 1.3.1 |

## Conan

```bash
cd archives/o/osm-pbf/1.6.1
conan create . -pr:h=ohos-aarch64-6.1 -pr:b=default
```

### test_package（R34）

- `test.cpp`：`#include <osmpbf/osmpbf.h>`，使用 `OSMPBF_VERSION` / 常量，并对 `OSMPBF::BlobHeader` 做 set/serialize/parse（强制链接 libosmpbf）。
- `build()`：必须 compile+link 成功；交叉环境跳过 qemu 运行，但**不做**仅检查文件存在的空壳测试。
- 可运行时：`ctest` + `osmpbf-outline sample.pbf`（断言 `OSMHeader`）。
- 消费者链接需 protobuf 头/库：`OHOS_DEPS_PREFIX` 或 test_package 自动拉取 cmd-pkgs。
