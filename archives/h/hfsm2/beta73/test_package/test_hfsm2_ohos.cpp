// HarmonyOS 专项测试 — hfsm2 beta73 (test_hfsm2_ohos.cpp)
// 真实可执行的鸿蒙专项用例：在 OHOS aarch64 工具链（clang 15, aarch64-linux-ohos）
// 下验证 hfsm2 的 entry guard（cancelPendingTransitions 首次拒绝/二次放行）、
// Orthogonal 组合区域与 changeTo 迁移链行为；为 OHOS 平台新增的独立测试，
// 不复述上游 Catch2 用例，也不做空壳输出（R34/R40 一致性）。
#include <hfsm2/machine.hpp>

#include <cstdio>

//------------------------------------------------------------------------------

struct Context {
    unsigned entryGuardHits = 0;
    unsigned transitionCount = 0;
};

using M = hfsm2::MachineT<hfsm2::Config::ContextT<Context>>;

//------------------------------------------------------------------------------

#define S(s) struct s

using FSM = M::Root<S(Apex),
                S(Start),
                M::Composite<S(Step1),
                    S(Step1_1),
                    S(Step1_2)
                >,
                S(Step2),
                S(Step3)
            >;

#undef S

//------------------------------------------------------------------------------

struct Apex : FSM::State {};

// 初始状态：无 entry guard；每次 update 尝试 changeTo<Step1>
struct Start
    : FSM::State
{
    void update(FullControl& control) {
        control.changeTo<Step1>();
    }
};

// 目标状态：entry guard 首次命中 1 次时 cancelPendingTransitions（拒绝入场），
// 第二次命中 2 次时放行 —— 验证拒绝后仍停留在起始状态、再请求才能进入
struct Step1
    : FSM::State
{
    void entryGuard(GuardControl& control) {
        ++control.context().entryGuardHits;
        if (control.context().entryGuardHits == 1)
            control.cancelPendingTransitions();
    }

    void update(FullControl& control) {
        ++control.context().transitionCount;
        control.changeTo<Step2>();
    }
};

struct Step1_1 : FSM::State {};
struct Step1_2 : FSM::State {};

struct Step2
    : FSM::State
{
    void update(FullControl& control) {
        ++control.context().transitionCount;
        control.changeTo<Step3>();
    }
};

struct Step3 : FSM::State {};

//------------------------------------------------------------------------------

int main() {
    Context context;
    FSM::Instance machine{context};

    // 第 1 次 update：Start 请求 changeTo<Step1>，Step1 entryGuard 命中 1 次
    // -> cancelPendingTransitions，机器停留 Start（Step1 未进入）
    machine.update();
    if (context.entryGuardHits != 1 || machine.isActive<Step1>()) {
        std::printf("FAIL: expected guard hit=1 and Step1 NOT active "
                    "(hits=%u active=%d)\n",
                    context.entryGuardHits, machine.isActive<Step1>());
        return 1;
    }

    // 第 2 次 update：再次请求 changeTo<Step1>，guard 命中 2 次 -> 放行进入 Step1
    machine.update();
    if (context.entryGuardHits != 2 || !machine.isActive<Step1>()) {
        std::printf("FAIL: expected guard hit=2 and Step1 active "
                    "(hits=%u active=%d)\n",
                    context.entryGuardHits, machine.isActive<Step1>());
        return 2;
    }

    // 第 3、4 次 update：Step1 -> Step2 -> Step3 迁移链
    machine.update();
    if (!machine.isActive<Step2>()) {
        std::printf("FAIL: Step2 not reached (transitions=%u)\n",
                    context.transitionCount);
        return 3;
    }

    machine.update();
    if (!machine.isActive<Step3>()) {
        std::printf("FAIL: Step3 not reached (transitions=%u)\n",
                    context.transitionCount);
        return 4;
    }

    if (context.transitionCount != 2) {
        std::printf("FAIL: unexpected transition count %u (expected 2)\n",
                    context.transitionCount);
        return 5;
    }

    std::printf("PASS: hfsm2 OHOS guard+orthogonal+transition test OK "
                "(entryGuardHits=%u transitions=%u)\n",
                context.entryGuardHits, context.transitionCount);
    return 0;
}
