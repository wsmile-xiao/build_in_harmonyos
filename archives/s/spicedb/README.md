# spicedb

SpiceDB 是一个开源的、基于 Google Zanzibar 理念的权限数据库（Authorization System）。它提供细粒度的关系型权限模型（Relationship-based Access Control, ReBAC），通过 gRPC/HTTP API 提供权限关系管理与鉴权查询能力，广泛应用于大规模权限、多租户授权与微服务场景。

- 上游主页：https://github.com/authzed/spicedb
- 许可证：Apache-2.0
- 语言：Go

## 功能特性
- Relationship-based access control（ReBAC，灵感来自 Google Zanzibar）
- 高性能权限图遍历与查询（Check / Expand / LookupSubjects / LookupResources）
- 多 datastore 支持（PostgreSQL、CockroachDB、MySQL、Spanner、内存模式）
- gRPC 与 HTTP API（含 OpenTelemetry 可观测性）
- Schema 语言定义权限模型，支持差分（Diff）与一致性校验

## 鸿蒙 PC 适配说明
- 纯 Go 静态二进制，`CGO_ENABLED=0`，`GOOS=linux`，支持 arm64 与 x86_64
- 版本 1.56.0 要求 Go 工具链 ≥ 1.26.5
- OHOS 上所有被执行的 ELF（含 `go test` 生成的测试二进制）需带 `.codesign` 段，由 binary-sign-tool 签名

## 使用示例
```sh
export GRPC_ADDR=127.0.0.1:50051
spicedb serve --grpc-addr=$GRPC_ADDR --grpc-preshared-key=testkey --datastore-engine=memory
spicedb version
```