// Consumer test for tweeny/3.
//
// Compiles the installed headers against the OHOS clang toolchain and asserts
// on documented interpolation behaviour. Single-value tweens use tweeny's
// scalar API (peek()/step() return T directly); multi-value tweens return
// std::tuple. Exit code: 0 = all checks passed, 1 = at least one check failed.
#include <tweeny.h>

#include <cmath>
#include <cstdio>
#include <tuple>

namespace {

int failures = 0;

void expect(bool ok, const char* what) {
    if (!ok) {
        ++failures;
        std::printf("FAIL: %s\n", what);
    }
}

bool near(float a, float b, float tol = 1e-3f) {
    return std::fabs(a - b) <= tol;
}

}  // namespace

int main() {
    // 1) Linear interpolation over a 10-unit duration (scalar API).
    auto linearTween = tweeny::from(0.0f).to(100.0f).during(10);
    expect(near(linearTween.peek(0.0f), 0.0f), "peek(0) == 0");
    expect(near(linearTween.peek(0.5f), 50.0f), "peek(0.5) == 50");
    expect(near(linearTween.peek(1.0f), 100.0f), "peek(1) == 100");

    linearTween.step(5);  // 5 of 10 time units
    expect(near(linearTween.peek(), 50.0f), "step(5) reaches halfway");
    expect(near(linearTween.progress(), 0.5f), "progress() == 0.5");
    linearTween.step(5);  // reach the end
    expect(near(linearTween.peek(), 100.0f), "step(5) reaches the end");
    expect(near(linearTween.progress(), 1.0f), "progress() == 1");

    // 2) Multi-value tween with heterogeneous types (std::tuple result).
    auto multi = tweeny::from(0, 1.0f).to(1200, 7.0f).during(1000);
    multi.seek(500);  // seek by time units
    expect(std::get<0>(multi.peek()) == 600, "int component at t=500");
    expect(near(std::get<1>(multi.peek()), 4.0f), "float component at t=500");

    // 3) seek() clamps out-of-range input and updates progress().
    auto chars = tweeny::from('a').to('z').during(25).via(tweeny::easing::linear);
    chars.seek(1.0f);
    expect(chars.peek() == 'z', "seek(1.0) lands on final value");
    chars.seek(-1.0f);
    expect(chars.peek() == 'a', "seek(-1.0) clamps to start");
    expect(near(chars.progress(), 0.0f), "progress() clamps to 0");

    // 4) Easing shape: quadraticInOut lags linear at 25%, meets it at 50%.
    auto line = tweeny::from(0.0f).to(100.0f).during(100).via(tweeny::easing::linear);
    auto ease = tweeny::from(0.0f).to(100.0f).during(100).via(tweeny::easing::quadraticInOut);
    float lineAt25 = line.peek(0.25f);
    float easeAt25 = ease.peek(0.25f);
    expect(easeAt25 < lineAt25, "quadraticInOut below linear at 25%");
    expect(near(ease.peek(0.5f), 50.0f, 1e-2f), "quadraticInOut midpoint == 50");

    // 5) onStep callback observes each stepped value.
    int stepCalls = 0;
    float lastValue = -1.0f;
    auto watched = tweeny::from(0.0f).to(10.0f).during(10);
    watched.onStep([&](tweeny::tween<float>&, float value) {
        ++stepCalls;
        lastValue = value;
        return false;
    });
    watched.step(3);
    expect(stepCalls == 1, "onStep fired exactly once");
    expect(near(lastValue, 3.0f), "onStep saw the interpolated value");

    // 6) Stepping past the end clamps to the final value.
    auto clamped = tweeny::from(0.0f).to(10.0f).during(10);
    clamped.step(999);
    expect(near(clamped.peek(), 10.0f), "overshoot clamps at end");

    if (failures == 0) {
        std::printf("ALL CHECKS PASSED\n");
        return 0;
    }
    std::printf("%d CHECK(S) FAILED\n", failures);
    return 1;
}
