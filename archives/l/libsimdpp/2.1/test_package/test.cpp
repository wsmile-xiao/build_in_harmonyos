// test_package consumer test — libsimdpp 2.1
// 实质使用被测包 API（R34）：make_int / add / store 并核对结果。
#include <simdpp/simd.h>

#include <cstdint>
#include <cstdio>

int main() {
    using namespace simdpp;

    int32<4> a = make_int(1, 2, 3, 4);
    int32<4> b = make_int(10, 20, 30, 40);
    int32<4> c = add(a, b);

    std::int32_t result[4];
    store(result, c);

    const std::int32_t expected[4] = {11, 22, 33, 44};
    bool ok = true;
    for (int i = 0; i < 4; ++i) {
        if (result[i] != expected[i]) {
            std::printf("libsimdpp test: FAIL lane %d got %d expected %d\n",
                        i, result[i], expected[i]);
            ok = false;
        }
    }
    if (ok) {
        std::printf("libsimdpp test: OK (11 22 33 44)\n");
    }
    return ok ? 0 : 1;
}