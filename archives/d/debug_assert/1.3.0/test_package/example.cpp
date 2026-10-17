// test_package consumer smoke test for debug_assert 1.3.0
// 上游 example.cpp 含必失败断言(1==0)，此处改为全部通过的断言；
// 并额外触发带自定义 handler 的模块，验证实质性 API 调用（R34）。
#include <debug_assert.hpp>

#include <cstdio>

//=== module A: default handler + level 1 ===//
struct module_a : debug_assert::default_handler,
                  debug_assert::set_level<1> {};

//=== module B: custom handler + level 2 ===//
struct module_b : debug_assert::set_level<2> {
    static void handle(const debug_assert::source_location& loc, const char* expression,
                       void* ptr = nullptr) noexcept
    {
        std::fprintf(stderr, "debug_assert module_b: %s (%s:%u) ptr=%p\n", expression,
                     loc.file_name, loc.line_number, static_cast<void*>(ptr));
    }
};

int main()
{
    int value = 42;
    // 通过性断言：不触发 handler
    DEBUG_ASSERT(2 + 2 == 4, module_a{});
    DEBUG_ASSERT(value == 42, module_a{}, debug_assert::level<1>{});
    // 自定义 handler 模块（断言为真，handler 不应被调用）
    DEBUG_ASSERT(value == 42, module_b{}, &value);
    DEBUG_ASSERT(value == 42, module_b{}, debug_assert::level<1>{}, &value);
    std::puts("debug_assert test_package OK");
    return 0;
}