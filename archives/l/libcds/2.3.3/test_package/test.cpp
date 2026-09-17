// Consumer test for libcds 2.3.3 — exercises the real public API:
// cds::Initialize/Terminate, Hazard Pointer GC lifecycle, the threading
// manager attach/detach, TreiberStack (LIFO) and MSQueue (FIFO).
// Prints one "CHECK <name>: PASS" line per check plus a trailing
// "RESULT: N passed, M failed" line parsed by conanfile.py into the
// HMBS_TEST_PACKAGE_RESULT machine-evidence marker.
#include <cstdio>

#include <cds/init.h>
#include <cds/gc/hp.h>
#include <cds/container/treiber_stack.h>
#include <cds/container/msqueue.h>

static int g_passed = 0;
static int g_failed = 0;

#define CHECK(name, expr)                                                     \
    do {                                                                      \
        if (expr) {                                                           \
            ++g_passed;                                                       \
            std::printf("CHECK %s: PASS\n", name);                            \
        }                                                                     \
        else {                                                                \
            ++g_failed;                                                       \
            std::printf("CHECK %s: FAIL\n", name);                            \
        }                                                                     \
    } while (0)

namespace {

bool check_treiber_stack_lifo()
{
    cds::container::TreiberStack<cds::gc::HP, int> stack;
    for (int i = 0; i < 5; ++i) {
        if (!stack.push(i))
            return false;
    }
    for (int i = 4; i >= 0; --i) {
        int value = -1;
        if (!stack.pop(value) || value != i)
            return false;
    }
    return stack.empty();
}

bool check_msqueue_fifo()
{
    cds::container::MSQueue<cds::gc::HP, int> queue;
    for (int i = 0; i < 5; ++i) {
        if (!queue.enqueue(i))
            return false;
    }
    for (int i = 0; i < 5; ++i) {
        int value = -1;
        if (!queue.dequeue(value) || value != i)
            return false;
    }
    return queue.empty();
}

} // namespace

int main()
{
    cds::Initialize();
    {
        cds::gc::HP hp;
        CHECK("hp-constructed", cds::gc::HP::isUsed());

        cds::threading::Manager::attachThread();
        CHECK("treiber-stack-lifo", check_treiber_stack_lifo());
        CHECK("msqueue-fifo", check_msqueue_fifo());
        cds::threading::Manager::detachThread();
    }
    cds::Terminate();

    std::printf("RESULT: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
