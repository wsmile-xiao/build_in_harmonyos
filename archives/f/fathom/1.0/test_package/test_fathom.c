/* test_fathom.c — installed-package consumer test for fathom/1.0.
 *
 * Calls the real public API of the packaged library (R34: no stubs),
 * without requiring Syzygy tablebase files:
 *   - tb_init() / TB_LARGEST empty-path contract;
 *   - tb_probe_wdl() / tb_probe_root() argument guards;
 *   - tablebase-free probing behavior: KvK is resolved as a draw by
 *     upstream's special case (move generation + root search run for
 *     real), while a position missing from the (empty) tables fails
 *     gracefully with TB_RESULT_FAILED;
 *   - the helper API bit ops, which execute the portability-patched
 *     popcount()/lsb() code paths (C fallbacks on non-x86 targets);
 *   - attack-table consistency behind those same paths.
 */
#include <stdio.h>

#include "tbprobe.h"

static int g_checks = 0;
static int g_failures = 0;

#define CHECK(cond) do { \
    g_checks++; \
    if (!(cond)) { \
        g_failures++; \
        printf("FAIL line %d: %s\n", __LINE__, #cond); \
    } else { \
        printf("pass line %d: %s\n", __LINE__, #cond); \
    } \
} while (0)

int main(void)
{
    /* 1) init contract: empty path initializes cleanly with no tablebases */
    CHECK(tb_init("") == true);
    CHECK(TB_LARGEST == 0);
    CHECK(tb_init(NULL) == true);   /* NULL is documented as "" */
    CHECK(TB_LARGEST == 0);

    /* KvK position: white king e4 (sq 28), black king e8 (sq 60) */
    const uint64_t white = (uint64_t)1 << 28;
    const uint64_t black = (uint64_t)1 << 60;
    const uint64_t kings = white | black;

    /* KQvK position: white king e4 (sq 28), white queen d1 (sq 3),
     * black king e8 (sq 60) */
    const uint64_t wq = white | ((uint64_t)1 << 3);
    const uint64_t queens = (uint64_t)1 << 3;

    /* 2) wrapper guards: castling / rule50 positions are not probeable */
    CHECK(tb_probe_wdl(white, black, kings, 0, 0, 0, 0, 0,
                       0, TB_CASTLING_K, 0, true) == TB_RESULT_FAILED);
    CHECK(tb_probe_wdl(white, black, kings, 0, 0, 0, 0, 0,
                       1, 0, 0, true) == TB_RESULT_FAILED);

    /* 3) tablebase-free probing: upstream resolves KvK as a draw with no
     *    files at all; a missing material signature fails gracefully */
    CHECK(tb_probe_wdl(white, black, kings, 0, 0, 0, 0, 0,
                       0, 0, 0, true) == TB_DRAW);
    CHECK(tb_probe_wdl(wq, black, kings, queens, 0, 0, 0, 0,
                       0, 0, 0, true) == TB_RESULT_FAILED);
    unsigned results[TB_MAX_MOVES];
    CHECK(tb_probe_root(white, black, kings, 0, 0, 0, 0, 0,
                        0, TB_CASTLING_K, 0, true, results)
          == TB_RESULT_FAILED);
    unsigned root = tb_probe_root(white, black, kings, 0, 0, 0, 0, 0,
                                  0, 0, 0, true, results);
    CHECK(root != TB_RESULT_FAILED);
    CHECK(TB_GET_WDL(root) == TB_DRAW);

    /* 4) helper API bit ops — these run the patched popcount()/lsb()
     *    fallback paths that non-x86 builds rely on */
    CHECK(tb_pop_count(0) == 0);
    CHECK(tb_pop_count(0xF0F0ull) == 8);
    CHECK(tb_pop_count(~0ull) == 64);
    CHECK(tb_lsb(1ull) == 0);
    CHECK(tb_lsb(1ull << 63) == 63);
    CHECK(tb_lsb(0x1040000000000100ull) == 8);
    CHECK(tb_pop_lsb(0x1040000000000100ull) == 0x1040000000000000ull);

    /* 5) attack tables stay consistent behind the patched lsb() */
    CHECK(tb_king_attacks(0) == 0x302ull);    /* a1 -> b1,a2,b2 */
    CHECK(tb_king_attacks(63) == 0x40C0000000000000ull); /* h8 -> g8,h7,g7 */
    CHECK(tb_pop_count(tb_king_attacks(28)) == 8);       /* e4: full ring */

    if (g_failures == 0)
        printf("FATHOM_TEST_PACKAGE_RESULT: PASS (%d/%d checks)\n",
               g_checks, g_checks);
    else
        printf("FATHOM_TEST_PACKAGE_RESULT: FAIL (%d/%d checks failed)\n",
               g_failures, g_checks);
    return g_failures == 0 ? 0 : 1;
}
