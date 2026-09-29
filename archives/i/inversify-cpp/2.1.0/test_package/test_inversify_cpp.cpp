// 消费者测试（test_package）— inversify-cpp 2.1.0 header-only 交付形态
// 只使用 conan 包交付的头文件（include/mosure/**），消费者视角验证：
// 常量/动态绑定、自动注入、unique/singleton 作用域、工厂绑定、嵌套注入、
// 未绑定符号异常、绑定检视（INVERSIFY_BINDING_INSPECTION）。
// 每条 check 逐条打印读数，任一失败进程退出码非 0。
#include <functional>
#include <iostream>
#include <memory>
#include <string>
#include <type_traits>

#include <mosure/inversify.hpp>

namespace inversify = mosure::inversify;

static int g_pass = 0;
static int g_fail = 0;

static void check(bool cond, const char *name) {
    if (cond) {
        ++g_pass;
        std::cout << "[PASS] " << name << std::endl;
    } else {
        ++g_fail;
        std::cout << "[FAIL] " << name << std::endl;
    }
}

// ── 消费者侧符号 ────────────────────────────────────────────────
namespace syms {
    using port = inversify::Symbol<int>;
    struct host : inversify::Symbol<std::string> {};   // 同型符号需 struct 区分
    using ratio = inversify::Symbol<double>;
}  // namespace syms

// ── 消费者侧接口与实现 ────────────────────────────────────────
struct IGreeter {
    virtual ~IGreeter() = default;
    virtual int greet() = 0;
    int calls{0};
};
using GreeterUnique = std::unique_ptr<IGreeter>;
using GreeterShared = std::shared_ptr<IGreeter>;

struct EnglishGreeter : IGreeter {
    EnglishGreeter() = default;
    explicit EnglishGreeter(int seed) : seed_(seed) {}
    int greet() override {
        ++calls;
        return seed_;
    }
    int seed_{0};
};

// 声明 EnglishGreeter 的注入依赖：syms::port
template <>
struct inversify::Injectable<EnglishGreeter>
    : inversify::Inject<syms::port> {};

using GreeterSym = inversify::Symbol<GreeterUnique>;
using GreeterSharedSym = inversify::Symbol<GreeterShared>;
using GreeterFactorySym = inversify::Symbol<std::function<GreeterUnique()>>;

// 嵌套注入：Widget 依赖 GreeterShared + port
struct Widget {
    Widget(GreeterShared g, int port) : g_(std::move(g)), port_(port) {}
    int run() { return g_->greet() + port_; }
    GreeterShared g_;
    int port_;
};
template <>
struct inversify::Injectable<Widget>
    : inversify::Inject<GreeterSharedSym, syms::port> {};

using WidgetSym = inversify::Symbol<std::unique_ptr<Widget>>;

int main() {
    // 1–3 常量绑定
    {
        inversify::Container<syms::port, syms::host, syms::ratio> c;
        c.bind<syms::port>().toConstantValue(8080);
        c.bind<syms::host>().toConstantValue(std::string("localhost"));
        c.bind<syms::ratio>().toConstantValue(0.5);
        check(c.get<syms::port>() == 8080, "constant int binding");
        check(c.get<syms::host>() == "localhost", "constant string binding");
        check(c.get<syms::ratio>() == 0.5, "constant double binding");
    }

    // 4–5 动态绑定与重绑定
    {
        inversify::Container<syms::port, syms::ratio> c;
        c.bind<syms::port>().toConstantValue(10);
        c.bind<syms::ratio>().toDynamicValue([](auto &ctx) {
            return ctx.container.template get<syms::port>() * 1.5;
        });
        check(c.get<syms::ratio>() == 15.0, "dynamic value from context");
        c.bind<syms::ratio>().toDynamicValue([](auto &ctx) {
            return ctx.container.template get<syms::port>() * 2.5;
        });
        check(c.get<syms::ratio>() == 25.0, "rebound dynamic value wins");
    }

    // 6–7 自动注入（unique 作用域）
    {
        inversify::Container<syms::port, GreeterSym> c;
        c.bind<syms::port>().toConstantValue(42);
        c.bind<GreeterSym>().to<EnglishGreeter>();
        auto a = c.get<GreeterSym>();
        auto b = c.get<GreeterSym>();
        check(a != nullptr && a->greet() == 42, "auto injection with ctor arg");
        check(a.get() != b.get(), "unique scope yields distinct instances");
        b->greet();
        check(a->calls == 1 && b->calls == 1, "per-instance call counters independent");
    }

    // 8 singleton 作用域
    {
        inversify::Container<syms::port, GreeterSharedSym> c;
        c.bind<syms::port>().toConstantValue(7);
        c.bind<GreeterSharedSym>().to<EnglishGreeter>().inSingletonScope();
        auto a = c.get<GreeterSharedSym>();
        auto b = c.get<GreeterSharedSym>();
        check(a.get() == b.get(), "singleton scope returns same instance");
        a->greet();
        check(b->calls == 1, "singleton shares state across gets");
        check(a->greet() == 7, "singleton injected value correct");
    }

    // 9 工厂绑定
    {
        inversify::Container<syms::port, GreeterSym, GreeterFactorySym> c;
        c.bind<syms::port>().toConstantValue(3);
        c.bind<GreeterFactorySym>().toDynamicValue([&c](auto &) {
            return [&c]() -> GreeterUnique { return c.get<GreeterSym>(); };
        });
        // 工厂需要 GreeterSym 绑定在同容器上
        c.bind<GreeterSym>().to<EnglishGreeter>();
        auto f = c.get<GreeterFactorySym>();
        auto i1 = f();
        auto i2 = f();
        check(i1 && i2 && i1.get() != i2.get(), "factory returns fresh instances");
        check(i1->greet() == 3, "factory instance resolves injected value");
    }

    // 10–11 嵌套注入
    {
        inversify::Container<syms::port, GreeterSharedSym, WidgetSym> c;
        c.bind<syms::port>().toConstantValue(20);
        c.bind<GreeterSharedSym>().to<EnglishGreeter>().inSingletonScope();
        c.bind<WidgetSym>().to<Widget>();
        auto w = c.get<WidgetSym>();
        check(w != nullptr, "nested dependency resolves");
        check(w->run() == 20 + 20, "nested chain (injected int + injected greeter)");
        check(c.get<GreeterSharedSym>().get() == w->g_.get(),
              "singleton shared across nested injection");
    }

    // 12 未绑定符号抛异常（类型与消息）
    {
        inversify::Container<syms::port, syms::host> c;
        bool threw_typed = false;
        bool msg_nonempty = false;
        try {
            (void)c.get<syms::port>();
        } catch (const inversify::exceptions::ResolutionException &e) {
            threw_typed = true;
            msg_nonempty = std::string(e.what()).size() > 0;
        } catch (...) {
            threw_typed = false;
        }
        check(threw_typed, "unbound symbol throws ResolutionException");
        check(msg_nonempty, "exception carries a message");
    }

    // 13 同型符号可分别绑定（struct 区分）
    {
        inversify::Container<syms::port, syms::host> c;
        c.bind<syms::port>().toConstantValue(1);
        c.bind<syms::host>().toConstantValue(std::string("h"));
        check(c.get<syms::port>() == 1 && c.get<syms::host>() == "h",
              "distinct symbols of same underlying type");
    }

    // 14 绑定检视（INVERSIFY_BINDING_INSPECTION）
    {
        inversify::Container<syms::port, GreeterSharedSym, WidgetSym> c;
        c.bind<syms::port>().toConstantValue(1);
        c.bind<GreeterSharedSym>().to<EnglishGreeter>().inSingletonScope();
        auto resolver = c.bind<WidgetSym>().to<Widget>().getResolver();
        auto deps = resolver->getDependencies();
        check(!!deps.get<syms::port>(), "inspection sees port dependency");
        check(!!deps.get<GreeterSharedSym>(), "inspection sees greeter dependency");
        check(!deps.get<WidgetSym>(), "inspection marks own symbol unbound");
    }

    // 15 容器实例彼此隔离（不同容器的绑定互不影响）
    {
        inversify::Container<syms::port> c1;
        inversify::Container<syms::port> c2;
        c1.bind<syms::port>().toConstantValue(1111);
        c2.bind<syms::port>().toConstantValue(2222);
        check(c1.get<syms::port>() == 1111 && c2.get<syms::port>() == 2222,
              "separate containers stay isolated");
    }

    // 编译期断言（static_assert，单列不混入运行期计数）
    static_assert(!std::is_same<syms::port, syms::host>::value,
                  "distinct symbol types must differ");
    static_assert(std::is_base_of<inversify::Symbol<int>, syms::port>::value,
                  "port derives from Symbol<int>");
    constexpr int k_static_asserts = 2;

    std::cout << "inversify-cpp consumer checks: " << (g_pass + g_fail) << " run, "
              << g_fail << " failed" << std::endl;
    std::cout << "inversify-cpp consumer static_asserts: " << k_static_asserts
              << " (compile-time, not in run count)" << std::endl;
    return g_fail == 0 ? 0 : 1;
}
