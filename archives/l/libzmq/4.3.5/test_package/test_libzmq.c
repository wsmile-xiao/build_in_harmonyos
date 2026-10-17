/* Consumer-side smoke + HarmonyOS-specific validation for libzmq 4.3.5.
 *
 * Exercises the documented C API surface that OHOS applications depend on:
 * inproc transport, tcp loopback transport, pub/sub fan-out, and the
 * platform-specific details that differ between glibc and OHOS musl
 * (errno values, pthread integration, clock_gettime-based timeouts).
 */
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include <zmq.h>

static int failures = 0;

#define CHECK(cond, label)                                       \
    do                                                           \
    {                                                            \
        if (cond)                                                \
        {                                                        \
            printf ("[PASS] %s\n", label);                       \
        }                                                        \
        else                                                     \
        {                                                        \
            printf ("[FAIL] %s (errno=%d %s)\n", label, errno,   \
                    zmq_strerror (errno));                       \
            failures++;                                          \
        }                                                        \
    } while (0)

/* HarmonyOS uses musl libc: verify the library-visible errno integration
 * used by zmq_errno()/zmq_strerror() works in the OHOS runtime. */
static void test_ohos_errno_and_strerror (void)
{
    const char *msg = zmq_strerror (EAGAIN);
    CHECK (msg != NULL && strlen (msg) > 0,
           "OHOS musl errno descriptions resolve via zmq_strerror");

    int major = 0, minor = 0, patch = 0;
    zmq_version (&major, &minor, &patch);
    CHECK (major == 4 && minor == 3, "linked libzmq reports version 4.3.x");
}

/* inproc:// transport: pure in-process queue, no kernel sockets needed. */
static void test_inproc_roundtrip (void)
{
    void *ctx = zmq_ctx_new ();
    CHECK (ctx != NULL, "zmq_ctx_new on OHOS");

    void *sender = zmq_socket (ctx, ZMQ_PAIR);
    void *receiver = zmq_socket (ctx, ZMQ_PAIR);
    CHECK (sender && receiver, "zmq_socket PAIR pair created");

    CHECK (zmq_bind (receiver, "inproc://ohos-test") == 0,
           "zmq_bind inproc endpoint");
    CHECK (zmq_connect (sender, "inproc://ohos-test") == 0,
           "zmq_connect inproc endpoint");

    const char *payload = "hello-harmonyos";
    CHECK (zmq_send (sender, payload, strlen (payload) + 1, 0) > 0,
           "zmq_send inproc message");

    /* Bounded receive so the consumer test fails fast instead of hanging
     * when an earlier step already failed. */
    int timeout_ms = 2000;
    zmq_setsockopt (receiver, ZMQ_RCVTIMEO, &timeout_ms,
                    sizeof (timeout_ms));

    char buffer[64];
    int received = zmq_recv (receiver, buffer, sizeof (buffer), 0);
    CHECK (received > 0 && strcmp (buffer, payload) == 0,
           "zmq_recv inproc roundtrip");

    zmq_close (sender);
    zmq_close (receiver);
    zmq_ctx_term (ctx);
}

/* tcp:// loopback: real kernel TCP sockets through the OHOS network stack. */
static void test_tcp_loopback_roundtrip (void)
{
    void *ctx = zmq_ctx_new ();
    void *rep = zmq_socket (ctx, ZMQ_REP);
    void *req = zmq_socket (ctx, ZMQ_REQ);
    CHECK (rep && req, "zmq_socket REQ/REP pair created");

    CHECK (zmq_bind (rep, "tcp://127.0.0.1:34567") == 0,
           "zmq_bind tcp loopback listener (OHOS TCP stack)");

    /* RCVTIMEO relies on clock_gettime(CLOCK_MONOTONIC) under musl. Both
     * directions get a timeout so a failed precondition fails fast. */
    int timeout_ms = 2000;
    zmq_setsockopt (rep, ZMQ_RCVTIMEO, &timeout_ms, sizeof (timeout_ms));
    zmq_setsockopt (req, ZMQ_RCVTIMEO, &timeout_ms, sizeof (timeout_ms));

    CHECK (zmq_connect (req, "tcp://127.0.0.1:34567") == 0,
           "zmq_connect tcp loopback");

    CHECK (zmq_send (req, "ping", 5, 0) > 0, "zmq_send tcp request");
    char buffer[64];
    int received = zmq_recv (rep, buffer, sizeof (buffer), 0);
    CHECK (received > 0 && strcmp (buffer, "ping") == 0,
           "zmq_recv tcp request");

    CHECK (zmq_send (rep, "pong", 5, 0) > 0, "zmq_send tcp reply");
    received = zmq_recv (req, buffer, sizeof (buffer), 0);
    CHECK (received > 0 && strcmp (buffer, "pong") == 0,
           "zmq_recv tcp reply (RCVTIMEO honored on OHOS)");

    zmq_close (rep);
    zmq_close (req);
    zmq_ctx_term (ctx);
}

/* PUB/SUB subscription filtering through the subscription trie. */
static void test_pubsub_filtering (void)
{
    void *ctx = zmq_ctx_new ();
    void *pub = zmq_socket (ctx, ZMQ_PUB);
    void *sub = zmq_socket (ctx, ZMQ_SUB);
    CHECK (pub && sub, "zmq_socket PUB/SUB pair created");

    CHECK (zmq_bind (pub, "inproc://ohos-pubsub") == 0,
           "zmq_bind pubsub endpoint");
    CHECK (zmq_connect (sub, "inproc://ohos-pubsub") == 0,
           "zmq_connect pubsub subscriber");

    const char topic[] = "harmony.";
    CHECK (zmq_setsockopt (sub, ZMQ_SUBSCRIBE, topic, strlen (topic)) == 0,
           "ZMQ_SUBSCRIBE topic prefix");

    zmq_sleep (1); /* let the subscription propagate */

    zmq_send (pub, "harmony.hello", 14, 0);
    zmq_send (pub, "other.dropped", 14, 0);

    char buffer[64];
    int received = zmq_recv (sub, buffer, sizeof (buffer), ZMQ_DONTWAIT);
    CHECK (received > 0 && strncmp (buffer, "harmony.", 8) == 0,
           "subscriber receives subscribed topic only");

    int timeout_ms = 300;
    zmq_setsockopt (sub, ZMQ_RCVTIMEO, &timeout_ms, sizeof (timeout_ms));
    received = zmq_recv (sub, buffer, sizeof (buffer), 0);
    CHECK (received == -1 && zmq_errno () == EAGAIN,
           "unsubscribed topic filtered out (EAGAIN on OHOS musl)");

    zmq_close (pub);
    zmq_close (sub);
    zmq_ctx_term (ctx);
}

/* pthread integration: OHOS NDK pthreads backing the zmq I/O thread. */
static void *worker_entry (void *arg)
{
    void *pusher = (void *) arg;
    zmq_send (pusher, "from-thread", strlen ("from-thread") + 1, 0);
    return NULL;
}

static void test_pthread_integration (void)
{
    void *ctx = zmq_ctx_new ();
    void *pull = zmq_socket (ctx, ZMQ_PULL);
    void *push = zmq_socket (ctx, ZMQ_PUSH);
    CHECK (pull && push, "zmq_socket PUSH/PULL pair created");

    CHECK (zmq_bind (pull, "inproc://ohos-threads") == 0,
           "zmq_bind thread pipeline endpoint");
    CHECK (zmq_connect (push, "inproc://ohos-threads") == 0,
           "zmq_connect thread pipeline");

    /* Bounded receive: if the worker thread failed to deliver, fail fast. */
    int timeout_ms = 2000;
    zmq_setsockopt (pull, ZMQ_RCVTIMEO, &timeout_ms, sizeof (timeout_ms));

    pthread_t worker;
    int rc = pthread_create (&worker, NULL, worker_entry, (void *) push);
    CHECK (rc == 0, "pthread_create works with libzmq on OHOS");

    if (rc == 0)
    {
        pthread_join (worker, NULL);
        char buffer[64];
        int received = zmq_recv (pull, buffer, sizeof (buffer), 0);
        CHECK (received > 0 && strcmp (buffer, "from-thread") == 0,
               "message produced on an OHOS pthread traverses the pipeline");
    }

    zmq_close (pull);
    zmq_close (push);
    zmq_ctx_term (ctx);
}

int main (void)
{
    printf ("== libzmq 4.3.5 HarmonyOS consumer test ==\n");

    test_ohos_errno_and_strerror ();
    test_inproc_roundtrip ();
    test_tcp_loopback_roundtrip ();
    test_pubsub_filtering ();
    test_pthread_integration ();

    if (failures == 0)
    {
        printf ("ALL HARMONYOS TESTS PASSED\n");
        return 0;
    }
    printf ("%d FAILURES\n", failures);
    return 1;
}
