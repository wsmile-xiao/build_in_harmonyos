/*
 * rcheevos consumer test (C) — HarmonyOS/OHOS aarch64.
 *
 * Real API usage of the packaged static library:
 *  1. rc_runtime_activate_achievement with a valid memaddr → RC_OK (parse)
 *  2. same with an INVALID memaddr → negative error code (negative control)
 *  3. rc_runtime_do_frame twice with a peek callback that satisfies the
 *     condition "0xH0004=1" → trigger state becomes RC_TRIGGER_STATE_TRIGGERED
 *  4. rc_error_str sanity
 *  5. rc_runtime_activate_lboard + get_lboard value formatting sanity
 */
#include <stdio.h>
#include <string.h>

#include <rc_runtime.h>
#include <rc_runtime_types.h>
#include <rc_error.h>

static int g_failures = 0;

#define CHECK(cond, msg)                                  \
    do {                                                  \
        if (!(cond)) {                                    \
            fprintf(stderr, "FAIL: %s\n", (msg));         \
            g_failures++;                                 \
        }                                                 \
    } while (0)

static unsigned g_frame = 0;
/* little-endian byte-backed memory: the 16-bit value at 0x0004 is 0 on
 * frames 0-1 (trigger passes through WAITING) and 1 from frame 2 on */
static unsigned char g_mem[8];

static uint32_t peek(uint32_t address, uint32_t num_bytes, void* ud)
{
    (void) ud;
    uint32_t v = 0;
    uint32_t i;
    for (i = 0; i < num_bytes && address + i < sizeof(g_mem); i++) {
        v |= (uint32_t)g_mem[address + i] << (8 * i);
    }
    return v;
}

static int g_achievement_triggered = 0;

static void on_event(const rc_runtime_event_t* ev)
{
    if (ev->type == RC_RUNTIME_EVENT_ACHIEVEMENT_TRIGGERED && ev->id == 1) {
        g_achievement_triggered = 1;
    }
}

int main(void)
{
    rc_runtime_t rt;

    /* 1. valid activation parses */
    rc_runtime_init(&rt);
    int rc_ok = rc_runtime_activate_achievement(&rt, 1, "0xH0004=1", NULL, 0);
    CHECK(rc_ok == RC_OK, "rc_runtime_activate_achievement(valid) == RC_OK");

    /* 2. invalid activation rejected (negative control) */
    int rc_bad = rc_runtime_activate_achievement(&rt, 2, "0xH0004=", NULL, 0);
    CHECK(rc_bad < 0, "rc_runtime_activate_achievement(invalid) < 0");
    CHECK(strcmp(rc_error_str(rc_bad), "OK") != 0, "rc_error_str(invalid) != OK");

    /* 3. false frames put the trigger in WAITING, then the first true frame
     * fires the public TRIGGERED event (upstream state machine semantics,
     * device-probe verified: 0,0,1 -> TRIGGERED) */
    for (g_frame = 0; g_frame < 4; g_frame++) {
        g_mem[4] = (unsigned char)((g_frame < 2) ? 0 : 1);
        g_mem[5] = 0;
        rc_runtime_do_frame(&rt, on_event, peek, NULL, NULL);
    }
    CHECK(g_achievement_triggered == 1,
          "RC_RUNTIME_EVENT_ACHIEVEMENT_TRIGGERED observed after false-then-true frames");
    CHECK(rc_runtime_get_achievement(&rt, 1) != NULL,
          "rc_runtime_get_achievement(1) != NULL");

    /* 4. error strings */
    CHECK(strcmp(rc_error_str(RC_OK), "OK") == 0, "rc_error_str(RC_OK) == \"OK\"");

    /* 5. leaderboard activation + value formatting */
    int lb = rc_runtime_activate_lboard(&rt, 7, "STA:0xH0000=1::CAN:0xH0000=2::SUB:0xH0000=3::VAL:0xH0004", NULL, 0);
    CHECK(lb == RC_OK, "rc_runtime_activate_lboard(valid) == RC_OK");
    char buf[64];
    int formatted = rc_runtime_format_lboard_value(buf, sizeof(buf), 12345, RC_FORMAT_VALUE);
    CHECK(formatted > 0 && strcmp(buf, "12,345") == 0,
          "rc_runtime_format_lboard_value(RC_FORMAT_VALUE, 12345) == \"12,345\" (upstream separator semantics)");

    rc_runtime_destroy(&rt);

    if (g_failures == 0) {
        printf("test_rcheevos: OK (runtime activate/tick/trigger, lboard, error strings)\n");
        return 0;
    }
    printf("test_rcheevos: FAILED (%d checks failed)\n", g_failures);
    return 1;
}
