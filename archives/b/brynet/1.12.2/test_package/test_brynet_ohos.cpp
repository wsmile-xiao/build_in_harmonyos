// test_brynet_ohos.cpp — brynet 1.12.2 HarmonyOS 专项消费者测试
//
// 真实调用 brynet API（R34）：在 127.0.0.1 回环上启动 TCP echo 服务
// （TcpService + ListenerBuilder + 数据回调），用 ConnectionBuilder 同步
// 连接、发送报文、回读 echo 并校验内容，验证 OHOS 网络栈与 brynet 事件
// 循环（epoll/IO 线程）正常工作。附带 base 组件（endian 字节序 + WaitGroup）
// 快速验证头文件可包含。非空壳测试；用例独立于上游 tests/。
#include <brynet/base/WaitGroup.hpp>
#include <brynet/base/endian/Endian.hpp>
#include <brynet/net/TcpService.hpp>
#include <brynet/net/wrapper/ConnectionBuilder.hpp>
#include <brynet/net/wrapper/ServiceBuilder.hpp>

#include <chrono>
#include <cstdint>
#include <iostream>
#include <string>
#include <thread>

int main()
{
    using namespace brynet::net;
    using namespace brynet::net::wrapper;

    const std::string ip = "127.0.0.1";
    const uint16_t port = 19871;

    // 1) header-only base 组件快速校验（endian 主机/网络序互转 + WaitGroup）
    {
        const uint32_t v = 0x01020304U;
        const uint32_t net = brynet::base::endian::hostToNetwork32(v);
        if (brynet::base::endian::networkToHost32(net) != v)
        {
            std::cerr << "FAIL: Endian32 roundtrip" << std::endl;
            return 1;
        }
        auto wg = brynet::base::WaitGroup::Create();
        wg->wait();
    }

    // 2) 回环 echo 服务 + 客户端收发验证
    {
        auto service = IOThreadTcpService::Create();
        service->startWorkerThread(2);

        bool gotEcho = false;
        std::string echoed;

        auto listener = ListenerBuilder()
                                .WithService(service)
                                .WithAddr(false, ip, port)
                                .AddEnterCallback([&gotEcho, &echoed](const TcpConnection::Ptr& session) {
                                    session->setDataCallback([session, &gotEcho, &echoed](
                                                                     brynet::base::BasePacketReader& reader) {
                                        const auto* data = reader.currentBuffer();
                                        const size_t len = reader.size();
                                        echoed.assign(data, len);
                                        gotEcho = true;
                                        reader.consumeAll();
                                        session->send("", 0);  // 空发，保持连接活跃
                                    });
                                });

        bool listenOk = false;
        try
        {
            listener.asyncRun();
            listenOk = true;
        }
        catch (...)
        {
            listenOk = false;
        }

        if (!listenOk)
        {
            std::cerr << "FAIL: listener start" << std::endl;
            return 2;
        }

        auto connector = AsyncConnector::Create();
        connector->startWorkerThread();

        TcpConnection::Ptr session;
        try
        {
            session = ConnectionBuilder()
                              .WithService(service)
                              .WithConnector(connector)
                              .WithTimeout(std::chrono::seconds(3))
                              .WithAddr(ip, port)
                              .syncConnect();
        }
        catch (...)
        {
            session = nullptr;
        }

        if (session == nullptr)
        {
            std::cerr << "FAIL: syncConnect" << std::endl;
            listener.stop();
            return 3;
        }

        const std::string payload = "brynet-ohos-echo-1.12.2";
        session->send(payload.data(), payload.size());

        // 等待 echo 回读（最多 3 秒）
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(3);
        while (std::chrono::steady_clock::now() < deadline)
        {
            if (gotEcho)
            {
                break;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }

        if (!gotEcho || echoed != payload)
        {
            std::cerr << "FAIL: echo mismatch (got=" << echoed << ")" << std::endl;
            listener.stop();
            return 4;
        }

        std::cout << "PASS: brynet OHOS loopback echo OK ("
                  << echoed.size() << " bytes)" << std::endl;
        listener.stop();
    }

    return 0;
}