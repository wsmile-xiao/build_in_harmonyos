# osm-pbf

OpenStreetMap PBF（Protocolbuffer Binary Format）相关工具与 C++ 库。

对齐 Homebrew formula [`osm-pbf`](https://formulae.brew.sh/formula/osm-pbf)：上游为 [OSM-binary](https://github.com/openstreetmap/OSM-binary)。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.6.1 | built | Homebrew stable；产物含 `libosmpbf` + `osmpbf-outline` |

## 依赖

| 软件 | 版本 | 用途 |
|------|------|------|
| protobuf | 34.1 | `.proto` 代码生成与链接 |
| abseil-cpp | 20260107.1 | protobuf 传递依赖 |
| zlib | 1.3.1 | `osmpbf-outline` 解压 PBF |

## 构建（Docker / OHOS SDK 6.1）

```bash
cd archives/o/osm-pbf/1.6.1
conan create . -pr:h=ohos-aarch64-6.1 -pr:b=default --build=missing
```

环境要求：

- OpenHarmony SDK 6.1.0.31（`OHOS_SDK_HOME` / `/opt/ohos-sdk-6.1`）
- OHOS Clang 15.0.4
- 宿主 x86_64 `protoc` 与目标 protobuf 主版本一致（配方会自动下载）
