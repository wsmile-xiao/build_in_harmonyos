// test_package.cc for sgc 3.6.0 consumer-side functional test.
//
// Exercises the core public API of sgc (upstream libsigc++)
// (signal/slot/connection/emit, bind adaptor, trackable) to validate that
// the packaged library links and behaves correctly on HarmonyOS PC (aarch64).
// This mirrors a subset of the upstream tests/test_signal.cc and
// tests/test_bind.cc contracts.
//
// R34: the source substantively invokes the tested package's API. Assertions
// use plain assert() checks (no external test framework dependency).

#include <sigc++/sigc++.h>

#include <cassert>
#include <cstdio>

namespace {

// A free function slot returning the sum of its arguments.
static int add(int a, int b) { return a + b; }

struct Emitter {
    sigc::signal<int(int)> sig;

    int emit(int v) { return sig.emit(v); }
};

struct Receiver : public sigc::trackable {
    int last = -1;
    int on_value(int v) {
        last = v;
        return v * 2;
    }
};

}  // namespace

int main() {
    // 1) Basic signal/slot/emit (upstream test_signal.cc contract).
    sigc::signal<int(int)> sig;
    auto conn = sig.connect([](int v) { return v + 1; });
    assert(conn.connected());
    int result = sig.emit(41);
    assert(result == 42 && "signal emit must return slot result");
    std::printf("[1] signal.emit(41) = %d\n", result);

    // 2) Connection disconnect.
    conn.disconnect();
    assert(!conn.connected());
    std::printf("[2] connection disconnected\n");

    // 3) bind adaptor (upstream test_bind.cc contract): bind add(_,10) to 32.
    auto bound = sigc::bind(&add, 10);
    int bound_result = bound(32);
    assert(bound_result == 42 && "bind must partially apply arguments");
    std::printf("[3] sigc::bind(add,10)(32) = %d\n", bound_result);

    // 4) trackable auto-disconnect (upstream test_trackable.cc contract).
    Emitter e;
    {
        Receiver r;
        e.sig.connect(sigc::mem_fun(r, &Receiver::on_value));
        int emitted = e.emit(7);
        assert(emitted == 14 && "member slot must run and return value");
        assert(r.last == 7 && "member slot must observe emitted value");
        std::printf("[4] member slot emitted(7) -> %d, r.last=%d\n", emitted, r.last);
    }  // r destroyed -> trackable auto-disconnects the slot.
    int after = e.emit(99);
    assert(after == 0 && "empty signal emit must return a default-constructed value");
    std::printf("[5] after receiver destroyed, emit(99) -> %d (auto-disconnected)\n", after);

    std::printf("test sgc 3.6.0: OK\n");
    return 0;
}
