# srpc (Sogou RPC)

> 基于 Sogou C++ Workflow 的高性能 RPC 框架，支持 SRPC / bRPC / tRPC / thrift 协议与 HTTP 服务。

## 简介

srpc 是搜狗开源的 RPC 框架，构建在 [workflow](https://github.com/sogou/workflow)
异步网络引擎之上。同一份 `.proto`/`.thrift` 描述可直接生成
srpc、百度 bRPC、腾讯 tRPC、标准 thrift 四种协议的客户端与服务端代码
（`srpc_generator` 是随包安装的 protoc 插件），并支持 gzip/zlib/snappy/lz4
四种消息压缩。

## OHOS 适配要点

- 依赖 workflow（OHOS 上需 `WORKFLOW_USE_THREAD_IOSERVICE` 宏，由 workflow
  包通过 `cpp_info.defines` 导出；本包已转达给消费者）。
- protobuf 使用制品仓 3.17.3：上游构建固定 C++14，protobuf ≥ 4.22 的
  生成代码依赖 abseil 需要 C++17，不兼容。
- 上游 `test/` 与 `tutorial/` 均不在主构建树内，上游测试由本包
  `build()` 内单独配置构建并运行。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| workflow | 1.1.0 | C++ 异步网络引擎 |
| protobuf | 3.17.3 | 消息序列化 + protoc |
| openssl | 3.5.6 | TLS |
| snappy | 1.2.2 | RPCCompressSnappy |
| lz4 | 1.10.0 | RPCCompressLz4 |
| zlib | 1.3.1 | RPCCompressGzip/Zlib |

## 功能验证

```bash
# 消费者视角：生成桩代码并跑真实 RPC 往返
conan create archives/s/srpc/0.10.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → CONSUMER_TEST_OK
```

## 参考

- [官方文档](https://github.com/sogou/srpc/blob/master/docs)
- [源码仓库](https://github.com/sogou/srpc)
