/*
 * test_nanomsgxx.cpp — test_package consumer for the `nanomsgxx` package (R34).
 *
 * Exercises the real nanomsgxx C++11 API shipped in nnxx/*.h:
 *   1. Create two nnxx::socket instances (SP/PAIR) — uses nnxx::SP,
 *      nnxx::PAIR constants and nnxx::socket (calls nn_socket under the hood).
 *   2. Bind one endpoint and connect the other over inproc:// transport.
 *   3. Send a message on socket1 and receive it on socket2, verifying the
 *      payload round-trips intact.
 * This proves the consumer can link against the packaged libnnxx (which in
 * turn links nanomsg) and call into it at runtime — not just a print-only
 * shell test.
 *
 * Build: clang++ test_nanomsgxx.cpp -Innxx -lnnxx -lnanomsg
 */
#include <nnxx/socket>
#include <nnxx/message>
#include <nnxx/nn.h>

#include <cstdio>
#include <string>
#include <cstring>

int main()
{
    const char *payload = "nanomsgxx test payload";

    /* Step 1 — create a pair of SP/PAIR sockets. */
    nnxx::socket s1(nnxx::SP, nnxx::PAIR);
    nnxx::socket s2(nnxx::SP, nnxx::PAIR);
    if (!s1 || !s2)
    {
        std::printf("FAIL: could not create nnxx sockets\n");
        return 1;
    }

    /* Step 2 — bind / connect over the in-process transport. */
    s1.bind("inproc://nnxx-test");
    s2.connect("inproc://nnxx-test");

    /* Step 3 — send on s1, receive on s2, verify round-trip. */
    int n = s1.send(payload, 0);
    if (n < 0)
    {
        std::printf("FAIL: send() returned %d\n", n);
        return 1;
    }

    nnxx::message msg = s2.recv();
    if (!msg)
    {
        std::printf("FAIL: recv() returned empty message\n");
        return 1;
    }

    const std::string received(static_cast<const char *>(msg.data()), msg.size());
    if (received != payload)
    {
        std::printf("FAIL: payload mismatch — got '%s'\n", received.c_str());
        return 1;
    }

    std::printf("test_nanomsgxx: PASS (round-trip '%s' over inproc://)\n",
                received.c_str());
    return 0;
}
