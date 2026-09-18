/*
 * Consumer test for minicoro 0.1.3 — OHOS aarch64.
 *
 * Uses ONLY the installed public header (minicoro.h) and the public
 * coroutine API: mco_desc_init / mco_create / mco_push / mco_pop /
 * mco_resume / mco_yield / mco_status / mco_destroy. Verifies observable
 * results of a real coroutine round-trip: storage exchange across
 * yield/resume and state transitions.
 */
#include <stdio.h>
#include <string.h>

#define MINICORO_IMPL
#include <minicoro.h>

static int failures = 0;

static void verify_condition(int condition, const char *message) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        failures++;
    }
}

/* Coroutine entry: reads one value from storage, yields it back, then dies. */
static void coro_entry(mco_coro *co) {
    int received = 0;

    verify_condition(mco_running() == co, "mco_running == co inside coroutine");
    verify_condition(mco_status(co) == MCO_RUNNING, "status == MCO_RUNNING inside");

    /* Pop the value pushed before first resume. */
    verify_condition(mco_get_bytes_stored(co) == sizeof(int),
                     "storage size == sizeof(int)");
    verify_condition(mco_pop(co, &received, sizeof(received)) == MCO_SUCCESS,
                     "mco_pop succeeds");
    verify_condition(received == 42, "popped value == 42");

    /* Push a result value and yield back to the caller. */
    int out = 7;
    verify_condition(mco_push(co, &out, sizeof(out)) == MCO_SUCCESS,
                     "mco_push succeeds");
    verify_condition(mco_yield(co) == MCO_SUCCESS, "mco_yield succeeds");
}

int main(void) {
    mco_coro *co = NULL;
    mco_desc desc = mco_desc_init(coro_entry, 0);
    desc.user_data = NULL;

    verify_condition(mco_create(&co, &desc) == MCO_SUCCESS, "mco_create succeeds");
    verify_condition(co != NULL, "co != NULL");
    verify_condition(mco_status(co) == MCO_SUSPENDED, "status == MCO_SUSPENDED");

    /* Send a value into the coroutine storage before first resume. */
    int in = 42;
    verify_condition(mco_push(co, &in, sizeof(in)) == MCO_SUCCESS,
                     "push 42 succeeds");
    verify_condition(mco_resume(co) == MCO_SUCCESS, "mco_resume succeeds");
    verify_condition(mco_status(co) == MCO_SUSPENDED,
                     "status == MCO_SUSPENDED after yield");

    /* Collect the value the coroutine pushed before yielding. */
    int out = 0;
    verify_condition(mco_get_bytes_stored(co) == sizeof(int),
                     "storage has 1 int after yield");
    verify_condition(mco_pop(co, &out, sizeof(out)) == MCO_SUCCESS,
                     "pop result succeeds");
    verify_condition(out == 7, "coroutine returned 7");

    /* Resume once more to let the coroutine finish. */
    verify_condition(mco_resume(co) == MCO_SUCCESS, "second mco_resume succeeds");
    verify_condition(mco_status(co) == MCO_DEAD, "status == MCO_DEAD after finish");
    verify_condition(mco_destroy(co) == MCO_SUCCESS, "mco_destroy succeeds");

    if (failures == 0) {
        puts("minicoro 0.1.3 consumer: 12 assertions passed");
    }
    return failures;
}