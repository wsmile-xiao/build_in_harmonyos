#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "embedmq.h"

/* Real consumer test: exercises the public API exactly as a downstream
 * application would — create dispatcher, register a named handler, post
 * a message, and verify the handler actually runs with the payload. */

static int g_count = 0;
static int g_last_value = -1;

typedef struct { int value; } int_msg_t;

static void handler_value(const void *data, size_t size, void *ctx)
{
    (void)ctx;
    assert(size == sizeof(int_msg_t));
    g_last_value = ((const int_msg_t *)data)->value;
    __atomic_fetch_add(&g_count, 1, __ATOMIC_SEQ_CST);
}

int main(void)
{
    embedmq_t *q = embedmq_create(NULL);
    assert(q != NULL);

    /* register a public handler */
    int r = embedmq_register(q, "consumer.test", handler_value, NULL);
    assert(r == EMBEDMQ_OK);

    /* duplicate registration must return EMBEDMQ_EXIST */
    r = embedmq_register(q, "consumer.test", handler_value, NULL);
    assert(r == EMBEDMQ_EXIST);

    /* post a payload message */
    int_msg_t m = { .value = 42 };
    r = embedmq_post(q, "consumer.test", &m, sizeof(m));
    assert(r == EMBEDMQ_OK);

    /* destroy drains the queue before returning: handler must have run */
    embedmq_destroy(q);
    assert(g_count == 1);
    assert(g_last_value == 42);

    printf("test_package consumer: embedmq public API OK (registered=%d delivered=%d value=%d)\n",
           g_count, g_count, g_last_value);
    return 0;
}
