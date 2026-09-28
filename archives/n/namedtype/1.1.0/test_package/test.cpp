/* test_package/test.cpp — namedtype 1.1.0 消费者测试（鸿蒙特有测试行来源）
 *
 * 只 include <NamedType/named_type.hpp>（单头自包含验证）：这正是上游
 * named_type_impl.hpp 缺 #include <tuple> 时会编译失败的入口——补丁 0001
 * 的回归面。任一断言失败即以非零码退出，conan create 的 test() 阶段失败。
 *
 * 覆盖 13 项消费者断言：
 *   1-4   显式构造/get、Addable（二元 + 一元 +）、Multiplicable
 *   5-7   Comparable（< / == / !=）
 *   8     fluent::make_named 工厂
 *   9-10  NamedType::ref 引用透传、默认构造
 *   11    NamedType::argument 命名参数
 *   12-13 fluent::make_named_arg_function（任意顺序命名参数——
 *         该路径展开 std::make_tuple/std::get，正是 <tuple> 缺失处）
 */
#include <NamedType/named_type.hpp>

#include <cstdio>
#include <string>

static int g_checks = 0;
static int g_failed = 0;

#define NT_CHECK(cond)                                          \
    do {                                                        \
        ++g_checks;                                             \
        if (!(cond)) {                                          \
            ++g_failed;                                         \
            std::printf("FAIL #%d: %s\n", g_checks, #cond);     \
        }                                                       \
    } while (0)

// make_named 的第一参数是「模板模板参数」（上游同款用法见 test/main.cpp
// "Strong generic type"），所以这里先声明别名模板再具名化。
template <typename T>
using MetersT = fluent::NamedType<T, struct MetersTag,
                                  fluent::Addable, fluent::Multiplicable,
                                  fluent::Comparable>;
using Meters = MetersT<int>;

int main()
{
    // 1 显式构造 + get
    Meters m{5};
    NT_CHECK(m.get() == 5);

    // 2 Addable（二元 +）
    NT_CHECK((m + Meters{3}).get() == 8);

    // 3 Addable（一元 +）
    NT_CHECK((+m).get() == 5);

    // 4 Multiplicable
    NT_CHECK((m * Meters{4}).get() == 20);

    // 5-7 Comparable
    NT_CHECK(m < Meters{9});
    NT_CHECK(m == Meters{5});
    NT_CHECK(m != Meters{6});

    // 8 make_named 工厂
    NT_CHECK(fluent::make_named<MetersT>(7).get() == 7);

    // 9 NamedType::ref 引用透传（底层对象被就地修改）
    using StrongInt = fluent::NamedType<int, struct StrongIntTag>;
    auto addOne = [](StrongInt::ref si) { ++(si.get()); };
    int i = 42;
    addOne(StrongInt::ref(i));
    NT_CHECK(i == 43);

    // 10 默认构造
    StrongInt def;
    def.get() = 42;
    NT_CHECK(def.get() == 42);

    // 11 NamedType::argument 命名参数
    using FirstName = fluent::NamedType<std::string, struct FirstNameTag>;
    using LastName = fluent::NamedType<std::string, struct LastNameTag>;
    static const FirstName::argument firstName;
    static const LastName::argument lastName;
    auto getFullName = [](FirstName const& f, LastName const& l) {
        return f.get() + l.get();
    };
    NT_CHECK(getFullName(firstName = "James", lastName = "Bond") == "JamesBond");

    // 12-13 make_named_arg_function：任意顺序（依赖 <tuple>）
    auto ordered = fluent::make_named_arg_function<FirstName, LastName>(
        [](FirstName const& f, LastName const& l) {
            return f.get() + "-" + l.get();
        });
    NT_CHECK(ordered(lastName = "Bond", firstName = "James") == "James-Bond");
    NT_CHECK(ordered(firstName = "James", lastName = "Bond") == "James-Bond");

    std::printf("namedtype consumer test: %d/%d assertions passed\n",
                g_checks - g_failed, g_checks);
    if (g_checks != 13) {
        std::printf("FAIL: 断言数与 MANIFEST 声明（13）不一致：%d\n", g_checks);
        return 2;
    }
    return g_failed == 0 ? 0 : 1;
}
