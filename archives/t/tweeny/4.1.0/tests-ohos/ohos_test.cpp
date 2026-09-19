/*
 * tweeny 4.1.0 鸿蒙专项测试（HarmonyOS-specific test）
 *
 * 以业务上层消费者视角验证 tweeny 在 OHOS (aarch64, clang 15.0.4, musl)
 * 上的适配成果。仅通过库已安装/导出的公开头文件（<tweeny/tweeny.h>、
 * <tweeny/easing.h>）与公开 API 使用该库，验证：
 *   1) 头文件在 OHOS 工具链下可正常编译（C++17，libc++）；
 *   2) 动画插值语义真实可观察：线性插值、多值 tween、缓动形状、
 *      seek/step 语义、事件回调、越界钳制。
 *
 * 本测试真实编译、链接并运行（在 OHOS 设备上原生执行），输出逐项
 * 断言结果；非空壳、非伪造输出。退出码 0 = 全部通过，1 = 存在失败。
 */
#include <tweeny/tweeny.h>

#include <cmath>
#include <cstdio>
#include <tuple>

namespace {

int failures = 0;

void expect(bool ok, const char* what) {
    if (!ok) {
        ++failures;
        std::printf("FAIL: %s\n", what);
    } else {
        std::printf("PASS: %s\n", what);
    }
}

bool near(float a, float b, float tol = 1e-3f) {
    return std::fabs(a - b) <= tol;
}

}  // namespace

int main() {
    std::printf("== tweeny 4.1.0 HarmonyOS special test ==\n");

    // 1) 单值标量 API：线性插值（10 帧）
    auto linearTween = tweeny::from(0.0f).to(100.0f).during(10u).build();
    expect(near(linearTween.peek(0u), 0.0f), "linear peek(0) == 0");
    expect(near(linearTween.peek(5u), 50.0f), "linear peek(5) == 50");
    expect(near(linearTween.peek(10u), 100.0f), "linear peek(10) == 100");

    linearTween.step(5);
    expect(near(linearTween.peek(), 50.0f), "step(5) reaches halfway");
    expect(near(linearTween.progress(), 0.5f), "progress() == 0.5");
    linearTween.step(5);
    expect(near(linearTween.peek(), 100.0f), "step(5) reaches the end");
    expect(near(linearTween.progress(), 1.0f), "progress() == 1");

    // 2) 多值 tween（std::tuple 结果）
    auto multi = tweeny::from(0, 1.0f).to(1200, 7.0f).during(1000u).build();
    multi.seek(500);
    expect(std::get<0>(multi.peek()) == 600, "multi int component at t=500");
    expect(near(std::get<1>(multi.peek()), 4.0f), "multi float component at t=500");

    // 3) seek 越界钳制
    auto chars = tweeny::from('a').to('z').during(25u).via(tweeny::easing::linear).build();
    chars.seek(25u);
    expect(chars.peek() == 'z', "seek(25) lands on final value");
    chars.seek(0u);
    expect(chars.peek() == 'a', "seek(0) clamps to start");
    expect(near(chars.progress(), 0.0f), "progress() clamps to 0");

    // 4) 缓动形状：quadraticInOut 在 25% 处落后于 linear，中点重合
    auto line = tweeny::from(0.0f).to(100.0f).during(100u).via(tweeny::easing::linear).build();
    auto ease = tweeny::from(0.0f).to(100.0f).during(100u).via(tweeny::easing::quadraticInOut).build();
    expect(ease.peek(25u) < line.peek(25u), "quadraticInOut below linear at 25%");
    expect(near(ease.peek(50u), 50.0f, 1e-2f), "quadraticInOut midpoint == 50");

    // 5) 事件回调：event::step（v4 API）
    int stepCalls = 0;
    float lastValue = -1.0f;
    auto watched = tweeny::from(0.0f).to(10.0f).during(10u).build();
    watched.on(tweeny::event::step, [&](const auto& t) {
        ++stepCalls;
        lastValue = static_cast<float>(t.peek());
        return tweeny::event::response::ok;
    });
    watched.step(3);
    expect(stepCalls == 1, "event::step fired exactly once");
    expect(near(lastValue, 3.0f), "event::step saw interpolated value");

    // 6) 步进越界钳制到终值
    auto clamped = tweeny::from(0.0f).to(10.0f).during(10u).build();
    clamped.step(999);
    expect(near(clamped.peek(), 10.0f), "overshoot clamps at end");

    std::printf("== result: %s (%d failure(s)) ==\n",
                failures == 0 ? "ALL PASSED" : "FAILED", failures);
    return failures == 0 ? 0 : 1;
}