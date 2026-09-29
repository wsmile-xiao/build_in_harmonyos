//
// rc_ptr 0.0.2 — test_package 消费者测试（HarmonyOS PC 适配）
//
// 消费者视角验证：从 conan 包交付的 include/ 真实 include <rc_ptr/rc_ptr.hpp> 并
// 调用 memory:: 公共 API，覆盖引用计数、弱引用、自定义 deleter、owner 序与数组访问。
// 断言一律用显式检查 + 计数器 + 非零退出码（不用 assert()：Release 下 -DNDEBUG
// 会把 assert 编译掉 → 假绿）。逐条打印 `[consumer] PASS`，末行输出合计。
//
// 另含 3 条 static_assert 编译期约束（element_type / 数组退化 / 异常类型）。
//
#include "rc_ptr/rc_ptr.hpp"

#include <cstddef>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <type_traits>
#include <utility>

// ── 编译期约束（3 条，不计入运行期断言数） ──
static_assert(std::is_same<memory::rc_ptr<int>::element_type, int>::value,
              "rc_ptr<int>::element_type must be int");
static_assert(std::is_same<memory::rc_ptr<int[]>::element_type, int>::value,
              "rc_ptr<int[]>::element_type must decay to int");
static_assert(std::is_class<memory::bad_weak_rc_ptr>::value,
              "memory::bad_weak_rc_ptr must be a class type");

static int g_pass = 0;
static int g_fail = 0;

static void check(bool cond, const char* name)
{
    if (cond)
    {
        ++g_pass;
        std::printf("[consumer] PASS %s\n", name);
    }
    else
    {
        ++g_fail;
        std::printf("[consumer] FAIL %s\n", name);
    }
}

// 读取**交付进包的那一份**头文件（不是源码树里的），断言内容指纹
static bool header_contains(const char* relative, const char* needle)
{
    const std::string path =
        std::string(RC_PTR_PKG_INCLUDE_DIR) + "/" + relative;
    std::ifstream in(path.c_str(), std::ios::binary);
    if (!in)
    {
        std::printf("[consumer] missing delivered header: %s\n", path.c_str());
        return false;
    }
    std::ostringstream buffer;
    buffer << in.rdbuf();
    return buffer.str().find(needle) != std::string::npos;
}

// enable_rc_from_this 的载体类型
struct node : public memory::enable_rc_from_this<node>
{
    int value = 42;
};

int main()
{
    // ── 交付面（2 条） ──
    check(header_contains("rc_ptr/rc_ptr.hpp", "class rc_ptr"),
          "delivered_header_contains_class_rc_ptr");
    check(header_contains("rc_ptr/rc_ptr.hpp", "class weak_rc_ptr"),
          "delivered_header_contains_class_weak_rc_ptr");

    // ── 默认构造与工厂（2 条） ──
    {
        memory::rc_ptr<int> empty;
        check(empty.get() == nullptr && empty.use_count() == 0 && !empty,
              "default_construction_use_count_0");
    }
    {
        memory::rc_ptr<int> made = memory::make_rc<int>(10);
        check(made.use_count() == 1 && *made == 10, "make_rc_single_owner");
    }

    // ── 拷贝 / 复位 / 移动 / 交换（4 条） ──
    {
        memory::rc_ptr<int> first{ new int{ 4 } };
        memory::rc_ptr<int> second = first;
        check(first.use_count() == 2 && second.get() == first.get(),
              "copy_increases_use_count");
    }
    {
        memory::rc_ptr<int>      host{ new int{ 3 } };
        memory::rc_ptr<int>      alias = host;
        host.reset();
        check(host.get() == nullptr && host.use_count() == 0 &&
                  alias.use_count() == 1 && *alias == 3,
              "reset_releases_owner");
    }
    {
        memory::rc_ptr<int> source{ new int{ 21 } };
        memory::rc_ptr<int> target;
        target = std::move(source);
        check(target.get() != nullptr && *target == 21 &&
                  source.get() == nullptr && source.use_count() == 0,
              "move_empties_source");
    }
    {
        memory::rc_ptr<int> first{ new int{ 1 } };
        memory::rc_ptr<int> second{ new int{ 2 } };
        first.swap(second);
        check(*first == 2 && *second == 1 && first.use_count() == 1 &&
                  second.use_count() == 1,
              "swap_exchanges_owners");
    }

    // ── 弱引用（3 条） ──
    {
        memory::rc_ptr<int>      live{ new int{ 5 } };
        memory::weak_rc_ptr<int> weak{ live };
        auto                     locked = weak.lock();
        check(locked.get() == live.get() && locked.use_count() == 2,
              "weak_lock_on_live_owner");
    }
    {
        memory::weak_rc_ptr<int> weak;
        {
            memory::rc_ptr<int> owner{ new int{ 9 } };
            weak = owner;
        }
        check(weak.expired() && weak.lock() == memory::rc_ptr<int>{},
              "weak_expired_after_owner_destroyed");

        bool threw = false;
        try
        {
            memory::rc_ptr<int> target;
            target = weak;
        }
        catch (const memory::bad_weak_rc_ptr&)
        {
            threw = true;
        }
        catch (...)
        {
        }
        check(threw, "assign_expired_weak_throws_bad_weak_rc_ptr");
    }

    // ── enable_rc_from_this（1 条） ──
    {
        memory::rc_ptr<node> owner{ new node() };
        memory::rc_ptr<node> same = owner->rc_from_this();
        check(same.get() == owner.get() && owner.use_count() == 2 &&
                  owner->value == 42,
              "enable_rc_from_this_rc_from_this");
    }

    // ── 自定义 deleter 只在最后一个持有者释放时调用一次（1 条） ──
    {
        std::size_t calls = 0;
        auto        deleter = [&calls](int* raw) {
            delete raw;
            ++calls;
        };
        using deleter_type = decltype(deleter)&;
        {
            memory::rc_ptr<int, deleter_type> owner{ new int{ 7 }, deleter };
            memory::rc_ptr<int, deleter_type> alias = owner;
            (void)alias;
        }
        check(calls == 1, "custom_deleter_called_once");
    }

    // ── owner_less 严格序（1 条） ──
    {
        memory::rc_ptr<int> first  = memory::make_rc<int>(1);
        memory::rc_ptr<int> second = memory::make_rc<int>(2);
        memory::owner_less<memory::rc_ptr<int>> less;
        check(less(first, second) != less(second, first),
              "owner_less_strict_order");
    }

    // ── bool / get / operator->（1 条） ──
    {
        memory::rc_ptr<std::pair<int, int>> pair{
            new std::pair<int, int>{ 26, 34 }
        };
        check(static_cast<bool>(pair) && pair.get() != nullptr &&
                  pair->first == 26 && pair->second == 34,
              "bool_get_arrow_operators");
    }

    // ── 数组下标访问（1 条） ──
    {
        memory::rc_ptr<int[]> array{ new int[4] };
        for (int i = 0; i < 4; ++i)
        {
            array[i] = i;
        }
        check(array[0] == 0 && array[1] == 1 && array[2] == 2 &&
                  array[3] == 3,
              "array_index_access");
    }

    // ── unique() 三态（1 条） ──
    {
        memory::rc_ptr<int> owner{ new int{ 1 } };
        bool                 ok = owner.unique() && owner.use_count() == 1;
        {
            memory::rc_ptr<int> alias = owner;
            ok = ok && !owner.unique() && owner.use_count() == 2;
        }
        ok = ok && owner.unique() && owner.use_count() == 1;
        check(ok, "unique_flag_three_states");
    }

    // ── 解引用（1 条） ──
    {
        constexpr int          value = 13;
        memory::rc_ptr<int>    ptr{ new int{ value } };
        check(*ptr == value, "dereference_operator_value");
    }

    std::printf("[consumer] TOTAL=%d FAIL=%d\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
