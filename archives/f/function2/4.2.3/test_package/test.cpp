#include <cstdio>
#include <functional>
#include "function2/function2.hpp"

int main() {
    fu2::function<int(int)> f = [](int x) { return x * 2; };
    int result = f(21);
    if (result != 42) {
        std::printf("test function2 4.2.3: FAILED (result=%d)\n", result);
        return 1;
    }
    std::printf("test function2 4.2.3: OK (result=%d)\n", result);
    return 0;
}
