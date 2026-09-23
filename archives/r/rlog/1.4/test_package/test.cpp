// 消费者测试（test_package）：真实调用 librlog 的公开 API 并断言行为。
// 覆盖：版本符号、通道注册/命名、订阅-发布链路、通道层级投递与过滤、
//       断言机制（rAssert → rlog::Error 的源码位置）、计时 API。
#include <rlog/rlog.h>
#include <rlog/Error.h>
#include <rlog/RLogChannel.h>
#include <rlog/RLogNode.h>
#include <rlog/RLogTime.h>

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

namespace {

int g_checks = 0;
int g_failures = 0;

void check(bool ok, const char *what)
{
    ++g_checks;
    if (!ok)
        ++g_failures;
    std::printf("[%s] %s\n", ok ? "PASS" : "FAIL", what);
}

// 捕获节点：通过公开虚函数 RLogNode::publish 接收消息，
// 用于验证订阅/发布链路与通道过滤。
class CaptureNode : public rlog::RLogNode
{
public:
    std::vector<std::string> messages;

protected:
    virtual void publish(const rlog::RLogData &data)
    {
        if (data.msg)
            messages.push_back(std::string(data.msg));
        rlog::RLogNode::publish(data);
    }
};

} // namespace

int main(int argc, char **argv)
{
    rlog::RLogInit(argc, argv);

    // 1) 库实现版本与头文件宏一致
    check(RLogVersion() == CURRENT_RLOG_VERSION,
          "RLogVersion() matches CURRENT_RLOG_VERSION");

    // 2)-3) 通道注册：按名字取回同一实例
    rlog::RLogChannel *chan = rlog::GetGlobalChannel("test/consumer", rlog::Log_Info);
    check(chan != 0 && chan->name() == "test/consumer",
          "GetGlobalChannel returns the requested channel name");
    check(rlog::GetGlobalChannel("test/consumer") == chan,
          "channel lookup returns the same instance");

    // 4)-5) 订阅-发布链路与消息格式化
    CaptureNode sink;
    sink.addPublisher(chan);
    chan->isInterested(&sink, true);

    rLog(chan, "value=%d", 42);
    check(sink.messages.size() == 1,
          "subscribed node receives messages published to the channel");
    check(!sink.messages.empty() &&
              sink.messages[0].find("value=42") != std::string::npos,
          "message formatting (%d) is applied");

    // 6) 通道层级：子通道消息投递给父通道订阅者
    rLog(rlog::GetGlobalChannel("test/consumer/detail", rlog::Log_Info),
         "detail message");
    check(sink.messages.size() == 2,
          "sub-channel messages reach the parent channel subscriber");

    // 7) 无关通道不投递
    rLog(rlog::GetGlobalChannel("test/other", rlog::Log_Info), "filtered out");
    check(sink.messages.size() == 2,
          "messages from an unrelated channel are filtered out");

    // 8)-9) 断言机制：rAssert 抛出 rlog::Error 且带消费者源码位置
    bool threw = false;
    try
    {
        rAssert(false);
    }
    catch (rlog::Error &err)
    {
        threw = true;
        check(err.file() != 0 && std::strstr(err.file(), "test.cpp") != 0,
              "rAssert error reports the consumer source file");
    }
    check(threw, "rAssert(false) throws rlog::Error");

    // 10)-11) 计时 API（RLogTime.h 的声明位于全局命名空间）
    rlog_time t0, t1;
    rlog_get_time(&t0);
    rlog_get_time(&t1);
    check(rlog_time_diff(t1, t0) >= 0,
          "rlog_get_time/rlog_time_diff are usable");
    check(rlog_time_unit() != 0 && std::strlen(rlog_time_unit()) > 0,
          "rlog_time_unit reports a unit");

    std::printf("rlog consumer test: checks=%d failures=%d\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
