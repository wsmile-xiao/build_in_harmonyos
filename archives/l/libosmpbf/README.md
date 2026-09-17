# libosmpbf

## 简介

OpenStreetMap PBF（Protocol buffer Binary Format）文件的 C++ 读写库，
上游为 openstreetmap/OSM-binary。PBF 是以 Google Protocol Buffers 为底层存储的
OSM 数据二进制格式；本库提供底层的 Blob / HeaderBlock / PrimitiveBlock 编解码。

## OHOS 适配

- OHOS 下强制 `CMAKE_SYSTEM_NAME=Linux`（device cmake 无 HarmonyOS 平台模块，E092 先例）
- 制品仓 protobuf 导出 `cmake_find_mode=none`，显式注入 `Protobuf_DIR` 与 protoc 路径
- 上游 C++ 无测试套件，以 `no_tests` 审计上报（c10t 先例）
- 上游恒产 static + shared，按 `shared` 选项在 package 阶段二选一

## 依赖

- protobuf/33.6
- zlib/1.3.1

## 功能验证

```cpp
#include <osmpbf/osmpbf.h>
// 链接 -losmpbf -lprotobuf -lz
OSMPBF::BlobHeader header;
header.set_type("OSMHeader");
```

## 参考

- 上游: https://github.com/openstreetmap/OSM-binary
- PBF 格式: https://wiki.openstreetmap.org/wiki/PBF_Format
