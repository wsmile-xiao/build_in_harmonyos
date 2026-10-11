/* test_bitstream.c - consumer test for the bitstream header-only library.
 *
 * Builds a synthetic MPEG-TS packet carrying a PAT section with the
 * library's writer API, then parses it back with the reader API and
 * asserts every field round-trips (the "synthetic TS stream" check).
 */
#include <stdio.h>

#include <bitstream/mpeg/ts.h>
#include <bitstream/mpeg/psi.h>
#include <bitstream/mpeg/psi/pat.h>
#include <bitstream/dvb/si.h>

static int g_checks = 0;

#define CHECK(cond, msg) \
    do { \
        if (!(cond)) { \
            printf("FAIL: %s\n", msg); \
            return 1; \
        } \
        g_checks++; \
    } while (0)

int main(void)
{
    TS_DECLARE(p_ts);        /* uint8_t p_ts[188] */
    uint8_t *p_pat, *p_patn;

    CHECK(TS_SIZE == 188, "TS_SIZE == 188");

    /* --- build a synthetic TS packet (PID 0x1234, unit start, payload) --- */
    ts_init(p_ts);
    CHECK(p_ts[0] == TS_SYNC, "ts_init writes sync byte 0x47");
    ts_set_pid(p_ts, 0x1234);
    CHECK(ts_get_pid(p_ts) == 0x1234, "ts pid round-trip");
    CHECK(!ts_get_unitstart(p_ts), "unit start initially clear");
    ts_set_unitstart(p_ts);
    CHECK(ts_get_unitstart(p_ts), "unit start set/get");
    CHECK(!ts_has_payload(p_ts), "payload flag initially clear");
    ts_set_payload(p_ts);
    CHECK(ts_has_payload(p_ts), "payload flag set/get");
    p_pat = ts_payload(p_ts);
    CHECK(p_pat == p_ts + 4, "payload starts right after the 4-byte TS header");

    /* --- carry a PAT section for one program (pn 1 -> PID 0x0100) --- */
    psi_init(p_pat, true);
    psi_set_tableid(p_pat, 0x00);          /* PAT */
    CHECK(psi_get_tableid(p_pat) == 0x00, "psi table id round-trip");
    psi_set_length(p_pat, 13);             /* 5 fixed + 1*4 program + 4 CRC */
    CHECK(psi_get_length(p_pat) == 13, "psi section length round-trip");
    p_patn = pat_get_program(p_pat, 0);
    patn_init(p_patn);
    patn_set_program(p_patn, 1);
    patn_set_pid(p_patn, 0x0100);
    CHECK(patn_get_program(p_patn) == 1, "pat program number round-trip");
    CHECK(patn_get_pid(p_patn) == 0x0100, "pat program pid round-trip");

    /* the dvb/si.h umbrella pulls in the whole DVB SI family; compiling
     * and reaching here proves that whole header stack is usable */
#ifdef __BITSTREAM_DVB_SI_H__
    CHECK(1, "dvb/si.h umbrella header compiles");
#endif

    printf("test_bitstream: %d checks ALL PASS\n", g_checks);
    return 0;
}
