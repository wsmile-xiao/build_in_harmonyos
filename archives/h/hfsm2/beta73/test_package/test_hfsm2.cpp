// test_package consumer test — hfsm2 beta73
// 真实调用 hfsm2 API：MachineT / Config::ContextT / PeerRoot / Composite /
// changeTo 过渡 + isActive 轮询，验证 header-only 库在 OHOS aarch64 下可被
// 消费者 include、编译并正确运行（R34：实质调用被测包 API，非空壳 print）。
#include <hfsm2/machine.hpp>

#include <cstdio>

//------------------------------------------------------------------------------

struct Context {
    unsigned cycles = 0;
};

using M = hfsm2::MachineT<hfsm2::Config::ContextT<Context>>;

//------------------------------------------------------------------------------

#define S(s) struct s

using FSM = M::PeerRoot<
                M::Composite<S(On),
                    S(Red),
                    S(Green)
                >,
                S(Off)
            >;

#undef S

//------------------------------------------------------------------------------

struct On
    : FSM::State
{
    void enter(Control& control) {
        control.context().cycles = 0;
    }
};

struct Red
    : FSM::State
{
    void update(FullControl& control) {
        if (control.context().cycles > 2)
            control.changeTo<Off>();
        else
            control.changeTo<Green>();
    }
};

struct Green
    : FSM::State
{
    void enter(Control& control) {
        ++control.context().cycles;
    }

    void update(FullControl& control) {
        control.changeTo<Red>();
    }
};

struct Off
    : FSM::State
{
    void enter(Control&) {
    }
};

//------------------------------------------------------------------------------

int main() {
    Context context;
    FSM::Instance machine{context};

    while (!machine.isActive<Off>())
        machine.update();

    if (context.cycles != 3) {
        std::printf("FAIL: hfsm2 transitions did not complete (cycles=%u)\n", context.cycles);
        return 1;
    }

    std::printf("PASS: hfsm2 header-only API OK (cycles=%u)\n", context.cycles);
    return 0;
}
