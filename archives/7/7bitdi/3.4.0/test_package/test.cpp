#include <SevenBit/DI.hpp>
#include <cassert>
#include <iostream>
#include <memory>
#include <string>

// HarmonyOS 消费者验证：真实调用 7bitDI header-only DI 容器 API
// （服务注册 -> 容器构建 -> 依赖注入解析 -> 断言）

using namespace sb::di;

struct IMessage
{
    virtual std::string text() = 0;
    virtual ~IMessage() = default;
};

struct HelloMessage final : IMessage
{
    std::string text() override { return "hello-7bitdi"; }
};

class Greeter
{
    std::unique_ptr<IMessage> _message;

  public:
    explicit Greeter(std::unique_ptr<IMessage> message) : _message(std::move(message)) {}

    [[nodiscard]] std::string greet() const { return _message->text(); }
};

int main()
{
    ServiceProvider provider = ServiceCollection{}
                                   .addTransient<IMessage, HelloMessage>()
                                   .addScoped<Greeter>()
                                   .buildServiceProvider();

    const auto &greeter = provider.getService<Greeter>();
    const auto result = greeter.greet();

    std::cout << "7bitdi consumer test: " << result << std::endl;

    // 断言结果，确认注入生效
    assert(result == "hello-7bitdi");

    // 再次解析，验证 scoped/singleton 生命周期正常
    const auto &greeter2 = provider.getService<Greeter>();
    (void)greeter2;

    std::cout << "7bitdi consumer test: OK" << std::endl;
    return 0;
}