#include <handy/net.h>
#include <handy/event_base.h>
#include <handy/logging.h>
#include <handy/slice.h>
#include <handy/util.h>
#include <handy/status.h>
#include <handy/conf.h>
#include <stdio.h>
#include <string>

using namespace std;
using namespace handy;

int main() {
    // Slice: the zero-dependency core value type.
    Slice s("hello handy");
    if (s.toString() != string("hello handy")) {
        printf("slice failed\n");
        return 1;
    }

    // util: format round-trip.
    string formatted = util::format("%s-%d", "handy", 42);
    if (formatted != "handy-42") {
        printf("format failed: %s\n", formatted.c_str());
        return 1;
    }

    // Conf: ini parser must fail on a missing file.
    Conf conf;
    if (conf.parse("nonexistent.ini") == 0) {
        printf("conf should fail on missing file\n");
        return 1;
    }

    // Ip4Addr: endpoint formatting.
    Ip4Addr loopback("127.0.0.1", 8080);
    if (loopback.toString() != "127.0.0.1:8080") {
        printf("ip4addr failed: %s\n", loopback.toString().c_str());
        return 1;
    }

    // EventBase loop + safeCall (exercises the epoll poller on OHOS).
    EventBase base;
    base.safeCall([] { info("consumer test task by base.safeCall"); });
    bool exited = false;
    base.runAfter(10, [&] {
        exited = true;
        base.exit();
    });
    base.loop();
    if (!exited) {
        printf("event loop did not run the timer\n");
        return 1;
    }

    printf("handy consumer test OK\n");
    return 0;
}
