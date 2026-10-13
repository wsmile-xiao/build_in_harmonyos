// Consumer test for cpp-ipc/1.3.0.
//
// Exercises the three public surfaces this package ships, all of them through
// the real library (no stubs): POSIX shared memory, the process shared named
// mutex and a broadcast channel that sends/receives through shared memory.
#include <cstdio>
#include <cstring>
#include <string>

#include "libipc/ipc.h"
#include "libipc/mutex.h"
#include "libipc/shm.h"

static int failures = 0;

#define CHECK(cond, msg)                                     \
    do {                                                     \
        if (cond) {                                          \
            std::printf("ok   : %s\n", msg);                 \
        } else {                                             \
            std::printf("FAIL : %s\n", msg);                 \
            ++failures;                                      \
        }                                                    \
    } while (0)

int main() {
    // 1) POSIX shared memory handle: create, map, read/write, release.
    {
        ipc::shm::handle h{"ohc_cpp_ipc_tpkg", 4096};
        CHECK(h.valid(), "shm::handle acquires a named region");
        CHECK(h.size() >= 4096, "shm::handle reports the requested size");
        auto* mem = static_cast<char*>(h.get());
        CHECK(mem != nullptr, "shm::handle::get() returns a mapped pointer");
        if (mem != nullptr) {
            std::memset(mem, 0, 32);
            std::strcpy(mem, "cpp-ipc-on-ohos");
            CHECK(std::strcmp(mem, "cpp-ipc-on-ohos") == 0,
                  "shared memory write/read round trip");
        }
        CHECK(h.ref() >= 1, "shm::handle ref count is tracked");
        h.release();
    }

    // 2) Process shared named mutex: open, lock, unlock, close.
    {
        ipc::sync::mutex m;
        CHECK(m.open("ohc_cpp_ipc_tpkg_mutex"), "sync::mutex opens by name");
        CHECK(m.lock(), "sync::mutex locks");
        CHECK(m.unlock(), "sync::mutex unlocks");
        m.close();
    }

    // 3) Broadcast channel: connect both ends, send and receive a message.
    {
        ipc::channel tx{"ohc_cpp_ipc_tpkg_chan", ipc::sender};
        ipc::channel rx{"ohc_cpp_ipc_tpkg_chan", ipc::receiver};
        CHECK(tx.valid() && rx.valid(), "channel connects as sender and receiver");
        CHECK(tx.send(std::string("ping")), "channel send");
        auto buf = rx.recv(1000);
        CHECK(!buf.empty(), "channel recv returns a message");
        if (!buf.empty()) {
            CHECK(std::strcmp(static_cast<char*>(buf.data()), "ping") == 0,
                  "channel payload matches what was sent");
        }
        tx.disconnect();
        rx.disconnect();
    }

    if (failures != 0) {
        std::printf("RESULT: FAILED (%d check(s))\n", failures);
        return 1;
    }
    std::printf("RESULT: PASS\n");
    return 0;
}
