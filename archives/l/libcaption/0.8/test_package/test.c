/*
 * Consumer test for libcaption 0.8.
 *
 * Links the real libcaption library and exercises the core CEA-608 /
 * caption_frame encode/decode API with deterministic input.
 *
 * Each CHECK() increments a passed counter and prints a pass line; a failed
 * check prints a FAIL line and increments a failed counter. The program exits
 * non-zero if any check failed, and always prints a final summary line:
 *   "CHECKS PASSED: N / TOTAL: M"
 */

#include "caption/caption.h"
#include "caption/eia608.h"

#include <stdio.h>
#include <string.h>

static int g_checks_passed = 0;
static int g_checks_failed = 0;
static int g_checks_total = 0;

#define CHECK(expr, name)                                                     \
    do {                                                                      \
        g_checks_total++;                                                     \
        if (expr) {                                                           \
            g_checks_passed++;                                                \
            printf("[PASS] %s\n", name);                                      \
        } else {                                                              \
            g_checks_failed++;                                                \
            printf("[FAIL] %s (line %d)\n", name, __LINE__);                  \
        }                                                                     \
    } while (0)

/* ------------------------------------------------------------------ */
/* 1. EIA-608 parity: odd parity must round-trip                       */
/* ------------------------------------------------------------------ */
static void test_parity(void)
{
    /* 0x41 = 'A' (7-bit). eia608_parity_byte sets bit 7 for odd parity. */
    uint8_t pb = eia608_parity_byte(0x41);
    /* odd parity of 0x41 (0b1000001, two set bits) => bit7 set => 0xC1 */
    CHECK(pb == 0xC1, "eia608_parity_byte(0x41) == 0xC1");

    /* parity word combines two bytes into one 16-bit cc word */
    uint16_t pw = eia608_parity_word(0x4142);
    CHECK(pw == 0xC1C2, "eia608_parity_word(0x4142) == 0xC1C2");

    /* verify a correctly-paritied word passes the verify check */
    CHECK(eia608_parity_varify(0xC1C2) == 1, "eia608_parity_varify(0xC1C2) == 1");

    /* a word with wrong parity must fail verify */
    CHECK(eia608_parity_varify(0x4142) == 0, "eia608_parity_varify(0x4142) == 0 (bad parity)");

    /* strip parity must recover the 7-bit payload */
    CHECK(eia608_parity_strip(0xC1C2) == 0x4142, "eia608_parity_strip(0xC1C2) == 0x4142");
}

/* ------------------------------------------------------------------ */
/* 2. EIA-608 control command round-trip                               */
/* ------------------------------------------------------------------ */
static void test_control_command(void)
{
    /* end_of_caption on channel 0 */
    uint16_t eoc = eia608_control_command(eia608_control_end_of_caption, 0);
    CHECK(eoc == eia608_parity(0x142F), "eia608_control_command(end_of_caption,0) round-trips");

    int cc = -1;
    eia608_control_t parsed = eia608_parse_control(eoc, &cc);
    CHECK(parsed == eia608_control_end_of_caption, "eia608_parse_control recovers end_of_caption");
    CHECK(cc == 0, "eia608_parse_control recovers channel 0");
}

/* ------------------------------------------------------------------ */
/* 3. UTF-8 <-> EIA-608 basic North American character round-trip      */
/* ------------------------------------------------------------------ */
static void test_utf8_roundtrip(void)
{
    /* 'A' is a basic North American character; channel 0 */
    uint16_t code = eia608_from_utf8_1("A", 0);
    CHECK(code != 0, "eia608_from_utf8_1('A',0) non-zero");

    int chan = -1;
    utf8_char_t c1[5] = {0}, c2[5] = {0};
    int ok = eia608_to_utf8(code, &chan, c1, c2);
    CHECK(ok != 0, "eia608_to_utf8(code) succeeds");
    CHECK(strcmp(c1, "A") == 0, "eia608_to_utf8 round-trips 'A'");
}

/* ------------------------------------------------------------------ */
/* 4. caption_frame pop-on flow: resume_loading -> write -> end_of_caption -> read */
/*    caption_frame_init() leaves frame->write == NULL, so a control    */
/*    command must first select the write buffer (pop-on uses back).    */
/* ------------------------------------------------------------------ */
static void test_caption_frame(void)
{
    caption_frame_t frame;
    caption_frame_init(&frame);

    /* 4a: after init, write pointer is NULL (no mode selected yet). */
    CHECK(caption_frame_popon(&frame) == 0, "after init popon()==0 (write NULL)");

    /* 4b: resume_caption_loading selects the back buffer (pop-on mode). */
    uint16_t rcl = eia608_control_command(eia608_control_resume_caption_loading, 0);
    libcaption_stauts_t st = caption_frame_decode(&frame, rcl, 0.0);
    CHECK(st == LIBCAPTION_OK, "caption_frame_decode(resume_caption_loading) == OK");
    CHECK(caption_frame_popon(&frame) == 1, "after resume_loading popon()==1 (write=back)");

    /* 4c: write a character to the back buffer. */
    int wr = caption_frame_write_char(&frame, 0, 0, eia608_style_white, 0, "H");
    CHECK(wr == 1, "caption_frame_write_char('H') returns 1");

    /* 4d: before end_of_caption, front buffer is empty (read returns ""). */
    eia608_style_t sty = eia608_style_white;
    int uln = -1;
    const utf8_char_t* rd0 = caption_frame_read_char(&frame, 0, 0, &sty, &uln);
    CHECK(rd0 != NULL && strcmp(rd0, "") == 0, "before EOC read_char(0,0) == '' (front empty)");

    /* 4e: end_of_caption copies back -> front (and clears back) but leaves
     *     the write pointer on the back buffer, so pop-on state is unchanged.
     *     The observable effect is that the front buffer now holds the text. */
    uint16_t eoc = eia608_control_command(eia608_control_end_of_caption, 0);
    st = caption_frame_decode(&frame, eoc, 0.0);
    CHECK(st == LIBCAPTION_READY, "caption_frame_decode(end_of_caption) == READY");
    CHECK(caption_frame_popon(&frame) == 1, "after EOC popon()==1 (write unchanged)");

    /* 4f: now front buffer holds 'H' (copied from back). */
    const utf8_char_t* rd = caption_frame_read_char(&frame, 0, 0, &sty, &uln);
    CHECK(rd != NULL && strcmp(rd, "H") == 0, "after EOC read_char(0,0) == 'H'");
}

int main(void)
{
    printf("=== libcaption 0.8 consumer test ===\n");
    test_parity();
    test_control_command();
    test_utf8_roundtrip();
    test_caption_frame();

    printf("\nCHECKS PASSED: %d / TOTAL: %d\n", g_checks_passed, g_checks_total);
    if (g_checks_failed != 0) {
        printf("RESULT: FAIL (%d checks failed)\n", g_checks_failed);
        return 1;
    }
    printf("RESULT: PASS (all %d checks passed)\n", g_checks_passed);
    return 0;
}
