#include <async_simple/coro/Lazy.h>
#include <async_simple/coro/SyncAwait.h>
#include <async_simple/executors/SimpleExecutor.h>
#include <iostream>

using namespace async_simple;
using namespace async_simple::coro;

Lazy<int> compute_value() {
    int sum = 0;
    for (int i = 1; i <= 100; ++i) {
        sum += i;
    }
    co_return sum;
}

int main() {
    executors::SimpleExecutor executor(1);
    auto lazy = compute_value();
    int result = syncAwait(lazy, &executor);

    if (result != 5050) {
        std::cerr << "FAIL: expected 5050, got " << result << std::endl;
        return 1;
    }
    std::cout << "PASS: async_simple coroutine computed sum(1..100) = " << result << std::endl;
    return 0;
}
