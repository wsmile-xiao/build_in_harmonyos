#include <cstdio>
#include <cstdlib>
#include <stdex/thread.hpp>
#include <stdex/mutex.hpp>

static int g_counter = 0;
static stdex::mutex g_mutex;

static void worker()
{
    for (int i = 0; i < 100; ++i)
    {
        g_mutex.lock();
        ++g_counter;
        g_mutex.unlock();
    }
}

int main(void)
{
    stdex::thread t1(worker);
    stdex::thread t2(worker);
    t1.join();
    t2.join();

    // Two threads * 100 increments each, guarded by stdex::mutex.
    bool ok = (g_counter == 200) && !t1.joinable() && !t2.joinable();
    std::printf("stdex consumer test: counter=%d expected=200 -> %s\n",
                g_counter, ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}