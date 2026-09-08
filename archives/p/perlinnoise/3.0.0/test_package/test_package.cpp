// test_package for perlinnoise 3.0.0 — real API usage (R34)
// Constructs siv::PerlinNoise, calls noise2D/octave2D with a fixed seed and
// verifies deterministic outputs, not just a print-only smoke test.
#include <cstdio>
#include <cmath>

#include <PerlinNoise.hpp>

int main() {
    // 固定种子 → 确定性输出
    siv::PerlinNoise noise{ 12345 };

    const double n1 = noise.noise2D(0.5, 0.5);
    const double n2 = noise.noise2D(0.5, 0.5);
    if (!std::isfinite(n1)) {
        std::fprintf(stderr, "FAIL: noise2D returned non-finite %f\n", n1);
        return 1;
    }
    if (n1 != n2) {
        std::fprintf(stderr, "FAIL: noise2D not deterministic (%f vs %f)\n", n1, n2);
        return 1;
    }
    if (n1 < -1.0 || n1 > 1.0) {
        std::fprintf(stderr, "FAIL: noise2D out of [-1,1]: %f\n", n1);
        return 1;
    }

    const double oct = noise.octave2D(0.25, 0.75, 4);
    if (!std::isfinite(oct)) {
        std::fprintf(stderr, "FAIL: octave2D returned non-finite %f\n", oct);
        return 1;
    }

    // 与上游示例同种子一致性的冒烟断言 (确定性回归)
    siv::PerlinNoise ref{ 12345 };
    const double r1 = ref.noise2D(0.5, 0.5);
    if (std::abs(r1 - n1) > 1e-12) {
        std::fprintf(stderr, "FAIL: same-seed instance mismatch (%f vs %f)\n", n1, r1);
        return 1;
    }

    std::printf("OK: perlinnoise noise2D=%.6f octave2D=%.6f verified\n", n1, oct);
    return 0;
}
