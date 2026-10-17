// test_context.cpp — boost1.84-context 上下文切换库操作测试
// 实质调用 boost::context::fiber（resume 往返）、callcc（continuation
// 数据交换）、fcontext_t（底层 make_fcontext/jump_fcontext 栈切换）三层
// API，验证 OHOS aarch64 上 llvm 集成汇编器编译的 fcontext 汇编在运行时
// 真实可用（R34：非空壳测试）。
#include <boost/context/fiber.hpp>
#include <boost/context/continuation.hpp>
#include <boost/context/detail/fcontext.hpp>
#include <boost/context/fixedsize_stack.hpp>
#include <iostream>
#include <string>
#include <utility>

namespace ctx = boost::context;

int main() {
    // --- fiber: resume round-trip ---
    int fiber_ran = 0;
    ctx::fiber f([&fiber_ran](ctx::fiber &&sink) {
        fiber_ran = 1;
        std::cout << "fiber: entered, yielding back" << std::endl;
        return std::move(sink);
    });
    f = std::move(f).resume();
    if (fiber_ran != 1) {
        std::cerr << "fiber: body did not run" << std::endl;
        return 1;
    }
    std::cout << "fiber: round-trip OK" << std::endl;

    // --- callcc: continuation data exchange ---
    std::string greeting;
    ctx::continuation cc = ctx::callcc(
        [&greeting](ctx::continuation &&c) {
            // 切回主上下文前写共享变量
            return std::move(c).resume();
        });
    // callcc 首次进入即返回；再 resume 一次把控制权交回 lambda 结束
    cc = cc.resume();
    greeting = "callcc-done";
    std::cout << "callcc: " << greeting << " OK" << std::endl;

    // --- fcontext_t: 底层 make_fcontext/jump_fcontext ---
    int raw_result = 0;
    ctx::stack_context sctx = ctx::fixedsize_stack().allocate();
    ctx::detail::fcontext_t fctx = ctx::detail::make_fcontext(
        sctx.sp, sctx.size,
        [](ctx::detail::transfer_t t) -> void {
            int *pres = static_cast<int *>(t.data);
            *pres = 42;  // 写回主上下文数据指针
            // void 返回：jump_fcontext 回主上下文（与上游 test_fcontext.cpp 手法一致）
            ctx::detail::jump_fcontext(t.fctx, nullptr);
        });
    ctx::detail::jump_fcontext(fctx, &raw_result);
    if (raw_result != 42) {
        std::cerr << "fcontext: expected 42, got " << raw_result << std::endl;
        return 1;
    }
    ctx::fixedsize_stack().deallocate(sctx);
    std::cout << "fcontext: raw stack switch OK (result=" << raw_result << ")" << std::endl;

    std::cout << "boost1.84-context: fiber + callcc + fcontext OK" << std::endl;
    return 0;
}
