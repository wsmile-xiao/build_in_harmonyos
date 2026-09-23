/* Consumer test for c-sig 3.8 (libsigc++ 3.8.0) — exercises the real
 * signals/slots API against the packaged libsigc-3.0 library: signal
 * connect/emit, return-value collection, connection and scoped_connection
 * lifetimes, sigc::trackable auto-disconnect, ptr_fun/mem_fun/bind slots.
 */

#include <stdio.h>
#include <stdlib.h>

#include <sigc++/sigc++.h>

#define ASSERT(cond, msg)                                             \
    do {                                                              \
        if (!(cond)) {                                                \
            fprintf(stderr, "FAIL line %d: %s\n", __LINE__, (msg));   \
            exit(1);                                                  \
        }                                                             \
    } while (0)

static int g_free_calls = 0;

static int add_two(int a, int b) { return a + b; }

static void count_call(int) { g_free_calls++; }

struct Counter : public sigc::trackable {
    int value = 0;
    int bump(int by) { value += by; return value; }
};

int main(void)
{
    /* --- 1. lambda slot: emit doubles the argument --- */
    sigc::signal<int(int)> doubler;
    doubler.connect([](int x) { return x * 2; });
    ASSERT(doubler.emit(21) == 42, "lambda slot: emit(21) != 42");

    /* --- 2. default collector returns the LAST slot's result --- */
    sigc::signal<int(int)> two_slots;
    two_slots.connect([](int x) { return x * 2; });
    two_slots.connect([](int x) { return x + 1; });
    ASSERT(two_slots.emit(21) == 22, "two slots: default collector != last result");

    /* --- 3. connection::disconnect() removes exactly one slot --- */
    sigc::signal<int(int)> connsig;
    sigc::connection first = connsig.connect([](int x) { return x * 2; });
    connsig.connect([](int x) { return x + 1; });
    ASSERT(first.connected(), "connection: should be connected before disconnect");
    first.disconnect();
    ASSERT(!first.connected(), "connection: disconnect() did not take effect");
    ASSERT(connsig.emit(21) == 22, "connection: disconnected slot still ran");

    /* --- 4. empty signal returns a value-initialized result --- */
    sigc::signal<int(int)> empty;
    ASSERT(empty.emit(9) == 0, "empty signal: emit() != value-initialized");

    /* --- 5. sigc::ptr_fun free-function slot --- */
    sigc::signal<void(int)> countersig;
    countersig.connect(sigc::ptr_fun(&count_call));
    countersig.emit(1);
    ASSERT(g_free_calls == 1, "ptr_fun: free function not called");

    /* --- 6. sigc::mem_fun member slot keeps object state --- */
    sigc::signal<int(int)> memsig;
    Counter counter;
    memsig.connect(sigc::mem_fun(counter, &Counter::bump));
    ASSERT(memsig.emit(5) == 5, "mem_fun: first emit != 5");
    ASSERT(memsig.emit(7) == 12, "mem_fun: accumulated emit != 12");
    ASSERT(counter.value == 12, "mem_fun: member state not updated");

    /* --- 7. sigc::trackable auto-disconnects when object dies --- */
    sigc::signal<int(int)> trackedsig;
    {
        Counter *heap_counter = new Counter();
        trackedsig.connect(sigc::mem_fun(*heap_counter, &Counter::bump));
        ASSERT(trackedsig.emit(3) == 3, "trackable: slot not callable while alive");
        delete heap_counter;
    }
    ASSERT(trackedsig.emit(3) == 0, "trackable: slot not auto-disconnected after delete");

    /* --- 8. sigc::scoped_connection disconnects on scope exit --- */
    sigc::signal<int(int)> scoped_sig;
    {
        sigc::scoped_connection sc =
            scoped_sig.connect([](int x) { return x * 10; });
        ASSERT(scoped_sig.emit(1) == 10, "scoped_connection: slot not callable in scope");
    }
    ASSERT(scoped_sig.emit(1) == 0, "scoped_connection: not disconnected at scope exit");

    /* --- 9. sigc::bind binds leading arguments --- */
    sigc::signal<int(int)> boundsig;
    boundsig.connect(sigc::bind(sigc::ptr_fun(&add_two), 40));
    ASSERT(boundsig.emit(2) == 42, "bind: bound slot != add_two(40, 2)");

    /* --- 10. slot is directly callable --- */
    sigc::slot<int(int)> direct = [](int x) { return x + 1; };
    ASSERT(direct(41) == 42, "slot: direct call != 42");

    /* --- 11. slot disconnecting itself during emit is safe --- */
    sigc::signal<int(int)> selfsig;
    sigc::connection keeper;
    keeper = selfsig.connect([&keeper](int x) {
        keeper.disconnect();
        return x;
    });
    ASSERT(selfsig.emit(7) == 7, "self-disconnect: emit during disconnect returned wrong value");
    ASSERT(!keeper.connected(), "self-disconnect: connection still connected");
    ASSERT(selfsig.emit(7) == 0, "self-disconnect: slot still invoked after self-disconnect");

    printf("test c-sig 3.8: PASS\n");
    return 0;
}
