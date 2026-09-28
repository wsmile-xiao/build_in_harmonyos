/*
 * test_liblms7compact — consumer integration test.
 *
 * liblms7002m.c is a compact MCU library whose SPI transport and logging
 * hooks are provided by the integrator.  This test provides strong
 * implementations of those hooks (as a real consumer would) and verifies
 * the library logic: register write sequences produced by the generated
 * lms7002m_defs.h macros, the reset/disable state machine and the
 * numeric CGEN tuning algorithm.
 */
#include "liblms7002m.h"

#include <stdio.h>
#include <string.h>

static uint32_t g_writes[128];
static unsigned g_writes_n = 0;

int lms7_spi_transact(struct lms7_state* s, uint16_t ival, uint32_t* oval)
{
    (void)s;
    *oval = ((uint32_t)ival << 16) | 0x1234u;
    return 0;
}

int lms7_spi_post(struct lms7_state* s, unsigned count, const uint32_t* regs)
{
    (void)s;
    if (g_writes_n + count > 128)
        return -1;
    memcpy(g_writes + g_writes_n, regs, count * sizeof(uint32_t));
    g_writes_n += count;
    return 0;
}

static int failures = 0;

#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        if (!(cond)) {                                                      \
            printf("FAIL: %s\n", msg);                                      \
            failures++;                                                     \
        }                                                                   \
    } while (0)

int main(void)
{
    struct lms7_state st;
    int r;

    memset(&st, 0, sizeof(st));
    st.fref = 100000000u;

    /* lms7_reset must post exactly 3 writes: 0x0020, 0x0020, 0x002E */
    g_writes_n = 0;
    r = lms7_reset(&st);
    CHECK(r == LMSE_OK, "lms7_reset returns LMSE_OK");
    CHECK(g_writes_n == 3, "lms7_reset posts 3 writes");
    if (g_writes_n >= 3) {
        CHECK(((g_writes[0] >> 16) & 0x7FFFu) == 0x0020u, "write[0] addr 0x0020");
        CHECK(((g_writes[1] >> 16) & 0x7FFFu) == 0x0020u, "write[1] addr 0x0020");
        CHECK(((g_writes[2] >> 16) & 0x7FFFu) == 0x002Eu, "write[2] addr 0x002E");
        CHECK((g_writes[0] & 0x80000000u) != 0, "write flag bit31 set");
    }

    /* lms7_disable must post 2 writes: 0x0081, 0x00A6 */
    g_writes_n = 0;
    r = lms7_disable(&st);
    CHECK(r == LMSE_OK, "lms7_disable returns LMSE_OK");
    CHECK(g_writes_n == 2, "lms7_disable posts 2 writes");
    if (g_writes_n >= 2) {
        CHECK(((g_writes[0] >> 16) & 0x7FFFu) == 0x0081u, "disable addr 0x0081");
        CHECK(((g_writes[1] >> 16) & 0x7FFFu) == 0x00A6u, "disable addr 0x00A6");
    }

    /* CGEN tuning exercises the numeric algorithm through SPI */
    g_writes_n = 0;
    r = lms7_cgen_tune(&st, 30000000u, 1);
    CHECK(r == LMSE_OK, "lms7_cgen_tune returns LMSE_OK");
    CHECK(g_writes_n > 0, "lms7_cgen_tune posts register writes");
    if (g_writes_n >= 5) {
        /* the CGEN tuning sequence is 5 registers: 0x0086..0x008B */
        CHECK(((g_writes[0] >> 16) & 0x7FFFu) == 0x0086u, "cgen write[0] addr 0x0086");
        CHECK(((g_writes[4] >> 16) & 0x7FFFu) == 0x008Bu, "cgen write[4] addr 0x008B");
    }

    if (failures == 0) {
        printf("test_liblms7compact: ALL TESTS PASSED\n");
        return 0;
    }
    printf("test_liblms7compact: %d FAILURES\n", failures);
    return 1;
}
