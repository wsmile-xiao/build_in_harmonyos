/* test_rtneural.cpp — real consumer test source for RTNeural 1.0.0 (L0c).

Links the header-only library and exercises the REAL API (R34) via
RTNeural::Dense1 (runtime dense layer): setWeights + setBias + forward,
verifying the output matches the manual dense computation.
*/
#include <cstdio>
#include <cmath>
#include <vector>
#include "RTNeural/RTNeural.h"
#include "RTNeural/dense/dense.h"

static int failures = 0;
#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        if (!(cond)) {                                                      \
            printf("FAIL: %s\n", msg);                                      \
            ++failures;                                                     \
        }                                                                   \
    } while (0)

int main(void)
{
    // Dense1(2) real forward: out = W*x + b
    RTNeural::Dense1<float> dense(2);
    std::vector<float> w{1.0f, 2.0f};   // 2 weights
    dense.setWeights(w.data());
    dense.setBias(0.5f);
    std::vector<float> x{3.0f, 4.0f};   // input
    float out = dense.forward(x.data());
    // expected: 1*3 + 2*4 + 0.5 = 11.5
    CHECK(std::fabs(out - 11.5f) < 1e-3f, "Dense1 forward");
    CHECK(std::fabs(dense.getWeight(1) - 2.0f) < 1e-3f, "getWeight");
    CHECK(std::fabs(dense.getBias() - 0.5f) < 1e-3f, "getBias");

    if (failures == 0)
        printf("OK: RTNeural 1.0.0 Dense1 real API ok\n");
    return failures == 0 ? 0 : 1;
}
