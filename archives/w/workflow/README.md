# Sogou Workflow

## 简介
搜狗开源的 C++ 并行计算与异步网络引擎。核心能力：
- 异步网络：HTTP/HTTPS、Redis、MySQL、DNS 协议的 client + server（内置实现，无外部客户端库依赖）
- 任务流：series/parallel、WFGraphTask DAG 图任务、counter/timer/go/thread 任务
- 算法任务：并行排序等
- 文件任务：异步 pread/pwrite（thread 版 IOService）
- UpstreamManager 负载均衡（round robin/加权随机/一致性哈希/manual）

## OHOS 适配
- 依赖仅 openssl/3.5.6（https/TLS）；redis/mysql/consul/upstream 为内置实现；KAFKA 组件默认关闭（上游默认形态）
- ⭐ OHOS 内核 AIO 的 RESFD 通知无效（io_submit 成功但 eventfd 永不唤醒）→ 补丁新增 USE_THREAD_IOSERVICE 选项切线程池版 IOService（接口一致，上游在 BSD/macOS 平台就走它）
- thread 版 IOService 布局与 linux 版不同：选择宏全局定义（跨翻译单元一致）+ 消费者侧通过 cpp_info.defines 传导
- musl msg_iovlen 类型修复（int vs size_t 窄化）
- 上游测试 38 项：37 通过 + 1 平台豁免（一致性哈希测试硬编码 libstdc++ std::hash 常量）
- test_package：WFHttpServer + HTTP 回环 200 OK

## 依赖
- openssl

## 使用示例
```cpp
#include <workflow/WFTaskFactory.h>
#include <workflow/WFHttpServer.h>

WFHttpServer server([](WFHttpTask *task) {
    task->get_resp()->append_output_body("Hello");
});
server.start("0.0.0.0", 8080);
```
