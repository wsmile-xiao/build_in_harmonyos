/* Consumer test for c-sig 3.8 (libsigc++ 3.8.0) — realistic event-bus /
 * observer scenario: dynamic listener subscription, per-connection
 * lifecycle (disconnect / block / unblock), sigc::trackable destruction
 * while subscribed, return-value collection, hide() adaptor, exception
 * propagation out of emit, and sigc::exception_catch keeping a multi-
 * listener emit alive when one listener throws.
 */

#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <sigc++/sigc++.h>

#include <stdio.h>
#include <stdlib.h>

#define ASSERT(cond, msg)                                             \
    do {                                                              \
        if (!(cond)) {                                                \
            fprintf(stderr, "FAIL line %d: %s\n", __LINE__, (msg));   \
            exit(1);                                                  \
        }                                                             \
    } while (0)

struct Listener : public sigc::trackable {
    std::string name;
    int hits = 0;
    int last_code = 0;

    explicit Listener(std::string n) : name(std::move(n)) {}

    void on_event(int code) {
        ++hits;
        last_code = code;
    }

    int on_query(int code) const { return code * static_cast<int>(name.size()); }
};

static int s_swallowed = 0;

struct SwallowCatcher {
    void operator()() const {
        try {
            throw;
        } catch (const std::range_error &) {
            ++s_swallowed;
        }
    }
};

int main(void)
{
    /* --- Event bus with three dynamically managed listeners --- */
    sigc::signal<void(int)> bus;
    auto alpha = std::make_unique<Listener>("alpha");
    auto beta = std::make_unique<Listener>("beta");
    auto gamma = std::make_unique<Listener>("gamma");
    sigc::connection c_alpha =
        bus.connect(sigc::mem_fun(*alpha, &Listener::on_event));
    sigc::connection c_beta =
        bus.connect(sigc::mem_fun(*beta, &Listener::on_event));
    sigc::connection c_gamma =
        bus.connect(sigc::mem_fun(*gamma, &Listener::on_event));

    bus.emit(7);
    ASSERT(alpha->hits == 1 && alpha->last_code == 7, "bus: alpha missed event 7");
    ASSERT(beta->hits == 1 && beta->last_code == 7, "bus: beta missed event 7");
    ASSERT(gamma->hits == 1 && gamma->last_code == 7, "bus: gamma missed event 7");

    /* --- Explicit disconnect of one subscription --- */
    /* libsigc++ 3.x connection::disconnect() returns void (2.x returned bool). */
    c_beta.disconnect();
    ASSERT(!c_beta.connected(), "bus: disconnect() did not invalidate connection");
    bus.emit(8);
    ASSERT(alpha->hits == 2 && beta->hits == 1, "bus: beta still notified after disconnect");
    ASSERT(gamma->hits == 2, "bus: gamma missed event 8");

    /* --- Listener object destroyed while subscribed (trackable) --- */
    gamma.reset();
    bus.emit(9); /* must not crash; alpha still notified */
    ASSERT(alpha->hits == 3 && alpha->last_code == 9, "bus: alpha missed event 9");

    /* --- Temporary blocking of one subscription --- */
    ASSERT(!c_alpha.block(), "bus: block() should report previous state false");
    ASSERT(c_alpha.blocked(), "bus: connection should be blocked");
    bus.emit(10);
    ASSERT(alpha->hits == 3, "bus: alpha notified while blocked");
    c_alpha.unblock();
    bus.emit(11);
    ASSERT(alpha->hits == 4 && alpha->last_code == 11, "bus: alpha missed event 11 after unblock");

    /* --- Query bus: last-value collector over member + lambda slots --- */
    sigc::signal<int(int)> queries;
    queries.connect(sigc::mem_fun(*alpha, &Listener::on_query)); /* "alpha" = 5 chars */
    queries.connect([](int code) { return code + 1; });
    ASSERT(queries.emit(3) == 4, "query bus: default collector != last slot result");

    /* --- hide() adaptor: subscribe a 0-arg provider to a 1-arg signal --- */
    sigc::signal<int(int)> provider_bus;
    provider_bus.connect(sigc::hide([]() { return 42; }));
    ASSERT(provider_bus.emit(123) == 42, "hide(): provider result not delivered");

    /* --- An exception escapes emit() --- */
    sigc::signal<void(int)> faulty;
    faulty.connect([](int) { throw std::range_error("boom"); });
    bool escaped = false;
    try {
        faulty.emit(1);
    } catch (const std::range_error &) {
        escaped = true;
    }
    ASSERT(escaped, "exception: did not propagate out of emit()");

    /* --- exception_catch keeps a multi-listener emit alive --- */
    sigc::signal<void(int)> resilient;
    resilient.connect(sigc::exception_catch(
        [](int) { throw std::range_error("boom2"); }, SwallowCatcher()));
    Listener normal("normal");
    resilient.connect(sigc::mem_fun(normal, &Listener::on_event));
    int before = s_swallowed;
    resilient.emit(5);
    ASSERT(s_swallowed == before + 1, "exception_catch: thrower's exception not swallowed");
    ASSERT(normal.hits == 1 && normal.last_code == 5, "exception_catch: later listener skipped after throw");

    printf("test c-sig 3.8 observer: PASS\n");
    return 0;
}
