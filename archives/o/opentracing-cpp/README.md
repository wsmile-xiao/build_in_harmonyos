# opentracing-cpp

分布式追踪（Distributed Tracing）的 C++11 实现，提供 OpenTracing API 的
标准接口（Tracer/Span/SpanContext/Propagation），支持 noop tracer、动态加载
（可选）与 mocktracer。

## 版本
- 1.5.1 (2026-09-16)

## 用途
- 分布式系统链路追踪埋点（开源标准 OpenTracing API）
- 被 Jaeger、Zipkin 等追踪系统的 C++ 客户端使用

## 安装
```bash
conan install --requires=opentracing-cpp/1.5.1 -r=ohpcd
```

## 使用
```cpp
#include <opentracing/tracer.h>
#include <opentracing/noop.h>
auto tracer = opentracing::MakeNoopTracer();
auto span = tracer->StartSpan("operation");
span->Finish();
```

## 验证
- ctest 上游测试 11/11 通过
- test_package 消费者用例通过（MakeNoopTracer/StartSpan/Finish）