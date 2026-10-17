// test.cpp — rtm 2.3.1 test_package 消费者验证（R34: 真实调用被测包 API）
//
// include rtm/vector4f.h 与 rtm/scalarf.h，执行向量加法/点积并断言结果。
// 任何数值偏差都会导致 exit != 0，从而让 `conan create` 的 test_package
// 阶段失败——这是实质功能测试，不是只打印字符串的空壳。

#include <cmath>
#include <cstdio>
#include <cstdlib>

#include "rtm/scalarf.h"
#include "rtm/vector4f.h"

int main() {
    rtm::vector4f a = rtm::vector_set(1.0f, 2.0f, 3.0f, 0.0f);
    rtm::vector4f b = rtm::vector_set(4.0f, 5.0f, 6.0f, 1.0f);

    rtm::vector4f sum = rtm::vector_add(a, b);
    rtm::vector4f expected_sum = rtm::vector_set(5.0f, 7.0f, 9.0f, 1.0f);
    rtm::vector4f diff = rtm::vector_sub(sum, expected_sum);
    float max_err = rtm::scalar_max(
        rtm::vector_get_x(rtm::vector_abs(diff)),
        rtm::scalar_max(
            rtm::vector_get_y(rtm::vector_abs(diff)),
            rtm::scalar_max(
                rtm::vector_get_z(rtm::vector_abs(diff)),
                rtm::vector_get_w(rtm::vector_abs(diff)))));

    float dot = rtm::vector_dot3(a, b);
    if (max_err > 1.0e-6f || std::fabs(dot - 32.0f) > 1.0e-6f) {
        std::fprintf(stderr,
                     "rtm test_package FAILED: max_err=%.9f dot=%.9f (expect 32)\n",
                     static_cast<double>(max_err), static_cast<double>(dot));
        return EXIT_FAILURE;
    }

    std::printf("rtm test_package OK: vector_add exact, dot3=%f\n",
                static_cast<double>(dot));
    return EXIT_SUCCESS;
}