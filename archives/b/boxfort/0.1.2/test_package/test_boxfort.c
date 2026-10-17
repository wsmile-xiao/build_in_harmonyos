/* Conan test_package consumer for boxfort 0.1.2.
 *
 * Exercises the public sandbox API against the installed static library:
 *   1. nested sandboxing (bxf_run inside a sandbox worker),
 *   2. exit-code propagation through the callback API,
 *   3. runtime quota enforcement (worker killed on timeout),
 *   4. bxf_context object round-trip into the sandbox.
 */
#include <stdio.h>
#include <stdlib.h>

#include "boxfort.h"

static int failures = 0;

#define CHECK(cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
        fflush(stderr); \
        ++failures; \
    } \
} while (0)

/* 1. nested sandbox */
static int nested_second(void)
{
    printf("nested worker ok\n");
    fflush(stdout);
    return 7;
}

static int nested_first(void)
{
    printf("outer worker ok\n");
    fflush(stdout);
    CHECK(!bxf_run(nested_second));
    return 0;
}

/* 2. exit-code propagation via callback */
static volatile int callback_seen;
static volatile int callback_exit = -1;

static int callback_child(void)
{
    return 5;
}

static void callback_cb(bxf_instance *instance)
{
    callback_exit = instance->status.exit;
    callback_seen = 1;
}

/* 3. runtime quota: the worker loops forever and must be killed */
static int busy_child(void)
{
    for (;;);
    return 0;
}

/* 4. context object round-trip */
static bxf_context g_ctx;

static int context_child(void)
{
    bxf_context ctx = bxf_context_current();

    if (!ctx)
        return 1;

    long *value = NULL;
    if (bxf_context_getobject(ctx, "answer", (void **) &value) < 0 || !value)
        return 2;
    if (*value != 42)
        return 3;
    return 0;
}

int main(void)
{
    /* 1. nested */
    CHECK(!bxf_run(nested_first));

    /* 2. callback */
    CHECK(!bxf_run(callback_child, .callback = callback_cb));
    while (!callback_seen);
    CHECK(callback_exit == 5);

    /* 3. runtime quota (sandbox killed after ~1s) */
    {
        bxf_instance *box = NULL;
        CHECK(!bxf_spawn(&box, busy_child, .quotas.runtime = 1.0));
        CHECK(!bxf_wait(box, BXF_FOREVER));
        CHECK(box->status.timed_out == 1);
        CHECK(box->status.alive == 0);
        bxf_term(box);
    }

    /* 4. context */
    CHECK(!bxf_context_init(&g_ctx));
    {
        long answer = 42;
        CHECK(!bxf_context_addobject(g_ctx, "answer", &answer,
                sizeof (answer)));
    }
    CHECK(!bxf_run(context_child, .inherit.context = g_ctx));
    CHECK(!bxf_context_term(g_ctx));

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        fflush(stderr);
        return 1;
    }
    printf("boxfort consumer: all checks passed\n");
    fflush(stdout);
    return 0;
}
