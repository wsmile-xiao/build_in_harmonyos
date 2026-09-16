/*
 * tests/test_wayneko.c — supplemented layer-1 behaviour suite for wayneko.
 *
 * Upstream wayneko (https://git.sr.ht/~leon_plickat/wayneko) ships NO test
 * target, NO tests/ directory and NO CI configuration (see MANIFEST.yml /
 * notes.md for the inventory evidence). This suite is added by the port to
 * exercise the REAL upstream code.
 *
 * It compiles the ACTUAL upstream wayneko.c into this translation unit with
 * its entry point renamed (main -> wayneko_cli_main) so the driver can link
 * the real translation unit and call its real (file-static) functions. No
 * upstream source file is modified.
 *
 * Every assertion is a real value check against computed expectations, with a
 * pass/fail counter and a non-zero exit status on any failure.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define main wayneko_cli_main
#include "wayneko.c"
#undef main

static int g_pass = 0;
static int g_fail = 0;

#define CHECK(cond, ...)                                                     \
    do {                                                                     \
        if (cond) {                                                          \
            g_pass++;                                                        \
        } else {                                                             \
            g_fail++;                                                        \
            fprintf(stderr, "  [FAIL] %s:%d: ", __FILE__, __LINE__);         \
            fprintf(stderr, __VA_ARGS__);                                    \
            fprintf(stderr, "\n");                                           \
        }                                                                    \
    } while (0)

/* Independent reimplementation of wayneko's documented colour maths, so the
 * assertions compare against a freshly computed expectation rather than
 * echoing the value under test. */
static void expect_colour(uint16_t r, uint16_t g, uint16_t b, uint16_t a,
                          pixman_color_t *out)
{
    out->alpha = (uint16_t)(((double)a / 255.0) * 65535.0);
    out->red   = (uint16_t)((((double)r / 255.0) * 65535.0) * out->alpha / 0xffff);
    out->green = (uint16_t)((((double)g / 255.0) * 65535.0) * out->alpha / 0xffff);
    out->blue  = (uint16_t)((((double)b / 255.0) * 65535.0) * out->alpha / 0xffff);
}

/* Parse a 0xRRGGBB[AA] literal the same way the code under test documents it. */
static void parse_hex(const char *hex, uint16_t *r, uint16_t *g, uint16_t *b,
                      uint16_t *a)
{
    *r = 0; *g = 0; *b = 0; *a = 255;
    if (4 != sscanf(hex, "0x%02hx%02hx%02hx%02hx", r, g, b, a))
        (void)sscanf(hex, "0x%02hx%02hx%02hx", r, g, b);
}

/* -- colour_from_hex / colour_from_flag / get_argument ------------------ */

static void test_colour_from_hex(void)
{
    pixman_color_t c;

    CHECK(colour_from_hex(&c, "0xFFFFFF") == true, "0xFFFFFF must be accepted");
    CHECK(c.alpha == 0xFFFF && c.red == 0xFFFF && c.green == 0xFFFF &&
              c.blue == 0xFFFF,
          "0xFFFFFF -> opaque white, got r=%u g=%u b=%u a=%u",
          c.red, c.green, c.blue, c.alpha);

    CHECK(colour_from_hex(&c, "0x000000") == true, "0x000000 must be accepted");
    CHECK(c.alpha == 0xFFFF && c.red == 0 && c.green == 0 && c.blue == 0,
          "0x000000 -> opaque black, got r=%u g=%u b=%u a=%u",
          c.red, c.green, c.blue, c.alpha);

    CHECK(colour_from_hex(&c, "0xFF000080") == true, "0xFF000080 must be accepted");
    CHECK(c.alpha == 32896, "0xFF000080 alpha should be 32896, got %u", c.alpha);
    CHECK(c.red == c.alpha && c.green == 0 && c.blue == 0,
          "0xFF000080 premultiplied red==alpha, got r=%u g=%u b=%u",
          c.red, c.green, c.blue);

    static const char *const ok[] = {
        "0x000000", "0xFFFFFF", "0x12AB34CD", "0x80808080",
        "0x00FF007F", "0x01020304", "0xABCDEF", "0xDEADBEEF",
    };
    for (size_t i = 0; i < sizeof(ok) / sizeof(ok[0]); i++) {
        uint16_t r, g, b, a;
        pixman_color_t exp;
        parse_hex(ok[i], &r, &g, &b, &a);
        expect_colour(r, g, b, a, &exp);
        bool rc = colour_from_hex(&c, ok[i]);
        CHECK(rc == true, "%s must be accepted", ok[i]);
        CHECK(memcmp(&c, &exp, sizeof(c)) == 0,
              "%s premultiplied mismatch (got r=%u g=%u b=%u a=%u)",
              ok[i], c.red, c.green, c.blue, c.alpha);
    }

    static const char *const bad[] = {
        "", "0x12345", "0xFFFFFFF", "FFFFFF", "0xGGGGGG",
        "0xFFFFFFAA00", "0x123456789", "zzzzzzzz",
    };
    for (size_t i = 0; i < sizeof(bad) / sizeof(bad[0]); i++) {
        pixman_color_t tmp;
        CHECK(colour_from_hex(&tmp, bad[i]) == false,
              "'%s' must be rejected", bad[i]);
    }
}

static void test_get_argument(void)
{
    char *argv2[] = { (char *)"prog", (char *)"value" };
    int i = 0;
    char *r = get_argument(2, argv2, &i);
    CHECK(r != NULL && strcmp(r, "value") == 0,
          "get_argument returns the following token");
    CHECK(i == 1, "get_argument advances the index, got %d", i);

    char *argv1[] = { (char *)"prog" };
    i = 0;
    r = get_argument(1, argv1, &i);
    CHECK(r == NULL, "get_argument returns NULL when the parameter is missing");
    CHECK(i == 0, "index must stay unchanged on missing parameter, got %d", i);

    char *argv3[] = { (char *)"prog", (char *)"a", (char *)"b" };
    i = 0;
    r = get_argument(3, argv3, &i);
    CHECK(r != NULL && strcmp(r, "a") == 0, "get_argument(i=0) -> argv[1]");
    i = 1;
    r = get_argument(3, argv3, &i);
    CHECK(r != NULL && strcmp(r, "b") == 0, "get_argument(i=1) -> argv[2]");
}

static void test_colour_from_flag(void)
{
    pixman_color_t c;
    char *ok[] = { (char *)"prog", (char *)"0x102030" };
    char *missing[] = { (char *)"prog" };
    char *malformed[] = { (char *)"prog", (char *)"nothex" };
    int i = 0;

    CHECK(colour_from_flag(&c, 2, ok, &i) == true, "valid flag value accepted");
    CHECK(i == 1, "flag parsed advances index, got %d", i);

    i = 0;
    CHECK(colour_from_flag(&c, 1, missing, &i) == false,
          "missing flag parameter rejected");

    i = 0;
    CHECK(colour_from_flag(&c, 2, malformed, &i) == false,
          "malformed flag value rejected");
}

/* -- atlas -------------------------------------------------------------- */

static void test_atlas(void)
{
    colour_from_hex(&bg_colour, "0xFFFFFF");
    colour_from_hex(&border_colour, "0x000000");

    CHECK(atlas_init() == true, "atlas_init() must succeed");
    CHECK(neko_atlas != NULL, "neko_atlas must be non-NULL after init");
    CHECK(neko_atlas_bg_fill != NULL, "neko_atlas_bg_fill must be non-NULL");
    CHECK(neko_atlas_border_fill != NULL, "neko_atlas_border_fill must be non-NULL");
    CHECK(pixman_image_get_width(neko_atlas) == neko_bitmap_width,
          "atlas width must equal neko_bitmap_width (%d), got %d",
          (int)neko_bitmap_width, pixman_image_get_width(neko_atlas));
    CHECK(pixman_image_get_height(neko_atlas) == neko_bitmap_height,
          "atlas height must equal neko_bitmap_height (%d), got %d",
          (int)neko_bitmap_height, pixman_image_get_height(neko_atlas));
    CHECK(neko_bitmap_stride == neko_bitmap_width / 8,
          "stride must be width/8 (%d), got %d",
          (int)(neko_bitmap_width / 8), neko_bitmap_stride);

    atlas_deinit();
    CHECK(neko_atlas == NULL && neko_atlas_bg_fill == NULL &&
              neko_atlas_border_fill == NULL,
          "atlas_deinit() must release every atlas image");
}

/* -- animation state machine -------------------------------------------- */

static void test_animation_setters(void)
{
    animation_neko_do_stare(false);
    CHECK(current_neko == NEKO_STARE && animation_ticks_until_next_frame == 10,
          "do_stare(false) -> STARE/10, got %d/%zu", (int)current_neko,
          animation_ticks_until_next_frame);

    animation_neko_do_stare(true);
    CHECK(current_neko == NEKO_STARE && animation_ticks_until_next_frame == 5,
          "do_stare(true) -> STARE/5, got %d/%zu", (int)current_neko,
          animation_ticks_until_next_frame);

    animation_neko_do_yawn();
    CHECK(current_neko == NEKO_YAWN && animation_ticks_until_next_frame == 5,
          "do_yawn -> YAWN/5, got %d/%zu", (int)current_neko,
          animation_ticks_until_next_frame);

    animation_neko_do_think();
    CHECK(current_neko == NEKO_THINK && animation_ticks_until_next_frame == 15,
          "do_think -> THINK/15, got %d/%zu", (int)current_neko,
          animation_ticks_until_next_frame);

    animation_neko_do_shock();
    CHECK(current_neko == NEKO_SHOCK && animation_ticks_until_next_frame == 3,
          "do_shock -> SHOCK/3, got %d/%zu", (int)current_neko,
          animation_ticks_until_next_frame);

    current_neko = NEKO_STARE;
    animation_neko_do_run_left();
    CHECK(current_neko == NEKO_RUN_LEFT_1 && animation_ticks_until_next_frame == 0,
          "do_run_left -> RUN_LEFT_1/0, got %d/%zu", (int)current_neko,
          animation_ticks_until_next_frame);
    animation_neko_do_run_left();
    CHECK(current_neko == NEKO_RUN_LEFT_2,
          "do_run_left toggles -> RUN_LEFT_2, got %d", (int)current_neko);
    animation_neko_do_run_left();
    CHECK(current_neko == NEKO_RUN_LEFT_1,
          "do_run_left toggles back -> RUN_LEFT_1, got %d", (int)current_neko);

    current_neko = NEKO_STARE;
    animation_neko_do_run_right();
    CHECK(current_neko == NEKO_RUN_RIGHT_1, "do_run_right -> RUN_RIGHT_1, got %d",
          (int)current_neko);
    animation_neko_do_run_right();
    CHECK(current_neko == NEKO_RUN_RIGHT_2,
          "do_run_right toggles -> RUN_RIGHT_2, got %d", (int)current_neko);

    current_neko = NEKO_SLEEP_1;
    animation_neko_do_sleep();
    CHECK(current_neko == NEKO_SLEEP_2 && animation_ticks_until_next_frame == 10,
          "do_sleep toggles SLEEP_1 -> SLEEP_2/10, got %d/%zu", (int)current_neko,
          animation_ticks_until_next_frame);

    current_neko = NEKO_SCRATCH_1;
    animation_neko_do_scratch();
    CHECK(current_neko == NEKO_SCRATCH_2 && animation_ticks_until_next_frame == 0,
          "do_scratch toggles SCRATCH_1 -> SCRATCH_2/0, got %d/%zu",
          (int)current_neko, animation_ticks_until_next_frame);
}

static void test_movement(void)
{
    surface.neko_x = 100;
    surface.prev_neko_x = 0;
    surface.width = 800;

    animation_neko_advance_left();
    CHECK(surface.neko_x == 85, "advance_left subtracts 15, got %u",
          (unsigned)surface.neko_x);
    CHECK(surface.prev_neko_x == 100, "advance_left records prev_neko_x, got %u",
          (unsigned)surface.prev_neko_x);

    animation_neko_advance_right();
    CHECK(surface.neko_x == 100, "advance_right adds 15, got %u",
          (unsigned)surface.neko_x);

    surface.neko_x = (uint16_t)(neko_x_advance + 1);
    CHECK(animation_can_run_left() == true, "can_run_left true when neko_x > %d",
          (int)neko_x_advance);
    surface.neko_x = neko_x_advance;
    CHECK(animation_can_run_left() == false,
          "can_run_left false when neko_x == %d", (int)neko_x_advance);

    surface.width = 800;
    surface.neko_x = (uint16_t)(800 - neko_size - neko_x_advance - 1);
    CHECK(animation_can_run_right() == true,
          "can_run_right true below width-size-advance (%u)", (unsigned)surface.neko_x);
    surface.neko_x = (uint16_t)(800 - neko_size - neko_x_advance);
    CHECK(animation_can_run_right() == false,
          "can_run_right false at width-size-advance (%u)", (unsigned)surface.neko_x);
}

static void test_idle_transitions(void)
{
    current_neko = NEKO_STARE;
    CHECK(animation_next_state_with_idle() == true,
          "idle transition from STARE reports a new frame");
    CHECK(current_neko == NEKO_YAWN && animation_ticks_until_next_frame == 5,
          "idle: STARE -> YAWN/5, got %d/%zu", (int)current_neko,
          animation_ticks_until_next_frame);

    current_neko = NEKO_SLEEP_1;
    CHECK(animation_next_state_with_idle() == true,
          "idle transition from SLEEP_1 reports a new frame");
    CHECK(current_neko == NEKO_SLEEP_2,
          "idle: SLEEP_1 -> do_sleep -> SLEEP_2, got %d", (int)current_neko);

    current_neko = NEKO_YAWN;
    CHECK(animation_next_state_with_idle() == true,
          "idle transition from YAWN reports a new frame");
    CHECK(current_neko == NEKO_SLEEP_1,
          "idle: YAWN -> do_sleep -> SLEEP_1, got %d", (int)current_neko);
}

static void test_hotspot_transitions(void)
{
    surface.neko_x = 100;
    surface.width = 800;

    current_neko = NEKO_STARE;
    CHECK(animation_next_state_with_hotspot(50) == true,
          "hotspot left of neko reports a new frame");
    CHECK(current_neko == NEKO_SHOCK && animation_ticks_until_next_frame == 3,
          "hotspot left: STARE -> SHOCK/3, got %d/%zu", (int)current_neko,
          animation_ticks_until_next_frame);

    current_neko = NEKO_STARE;
    CHECK(animation_next_state_with_hotspot(500) == true,
          "hotspot right of neko reports a new frame");
    CHECK(current_neko == NEKO_SHOCK, "hotspot right: STARE -> SHOCK, got %d",
          (int)current_neko);

    surface.neko_x = 100;
    current_neko = NEKO_RUN_LEFT_1;
    CHECK(animation_next_state_with_hotspot(10) == true,
          "running left with room reports a new frame");
    CHECK(surface.neko_x == 85, "running left advanced, got %u",
          (unsigned)surface.neko_x);
    CHECK(current_neko == NEKO_RUN_LEFT_2,
          "running left toggled frame -> RUN_LEFT_2, got %d", (int)current_neko);

    surface.neko_x = neko_x_advance;
    current_neko = NEKO_RUN_LEFT_1;
    CHECK(animation_next_state_with_hotspot(0) == true,
          "blocked run-left still reports a new frame");
    CHECK(current_neko == NEKO_STARE && animation_ticks_until_next_frame == 5,
          "blocked run-left -> STARE/5, got %d/%zu", (int)current_neko,
          animation_ticks_until_next_frame);
}

static void test_next_state_dispatch(void)
{
    struct Seat s;
    memset(&s, 0, sizeof(s));
    wl_list_init(&seats);

    animation_ticks_until_next_frame = 3;
    CHECK(animation_next_state() == false,
          "next_state with pending ticks reports no new frame");
    CHECK(animation_ticks_until_next_frame == 2,
          "pending ticks decrement to 2, got %zu", animation_ticks_until_next_frame);

    animation_ticks_until_next_frame = 1;
    CHECK(animation_next_state() == false,
          "next_state with 1 pending tick reports no new frame");
    CHECK(animation_ticks_until_next_frame == 0,
          "pending ticks decrement to 0, got %zu", animation_ticks_until_next_frame);

    surface.neko_x = 100;
    surface.width = 800;
    wl_list_insert(&seats, &s.link);
    s.currently_idle = true;
    current_neko = NEKO_STARE;
    animation_ticks_until_next_frame = 0;
    CHECK(animation_next_state() == true, "idle seat yields a new frame");
    CHECK(current_neko == NEKO_YAWN,
          "idle seat takes precedence -> YAWN, got %d", (int)current_neko);
    wl_list_remove(&s.link);

    current_neko = NEKO_SHOCK;
    animation_ticks_until_next_frame = 0;
    CHECK(animation_next_state() == true, "normal transition reports a new frame");
    CHECK(current_neko >= NEKO_SLEEP_1 && current_neko <= NEKO_RUN_LEFT_2,
          "current_neko stays a valid enum value, got %d", (int)current_neko);
    CHECK(current_neko == NEKO_STARE || current_neko == NEKO_YAWN,
          "SHOCK leaves to STARE or YAWN, got %d", (int)current_neko);
    CHECK(animation_ticks_until_next_frame == 5 ||
              animation_ticks_until_next_frame == 10,
          "resulting frame delay is 5 or 10, got %zu",
          animation_ticks_until_next_frame);
}

/* -- misc helpers & defaults -------------------------------------------- */

static void test_timespec_diff(void)
{
    struct timespec a, b, r;

    a.tv_sec = 5; a.tv_nsec = 300000000L;
    b.tv_sec = 2; b.tv_nsec = 100000000L;
    timespec_diff(&a, &b, &r);
    CHECK(r.tv_sec == 3 && r.tv_nsec == 200000000L,
          "timespec_diff 5.3-2.1 = 3.2, got %ld.%09ld",
          (long)r.tv_sec, (long)r.tv_nsec);

    a.tv_sec = 5; a.tv_nsec = 100000000L;
    b.tv_sec = 2; b.tv_nsec = 300000000L;
    timespec_diff(&a, &b, &r);
    CHECK(r.tv_sec == 2 && r.tv_nsec == 800000000L,
          "timespec_diff 5.1-2.3 = 2.8 (borrow), got %ld.%09ld",
          (long)r.tv_sec, (long)r.tv_nsec);
}

static void test_wants_sleep(void)
{
    time_t now = time(NULL);
    struct tm tm = *localtime(&now);
    bool expected = tm.tm_hour >= 23 || tm.tm_hour <= 6;
    CHECK(animtation_neko_wants_sleep() == expected,
          "wants_sleep must match local hour %d (expected %d)", tm.tm_hour,
          (int)expected);
}

static void test_buffer_randomize(void)
{
    char buf[16];
    memset(buf, 0, sizeof(buf));
    buffer_randomize_string(buf, sizeof(buf));

    bool in_range = true;
    for (size_t i = 0; i < sizeof(buf); i++) {
        if (buf[i] < 'A' || buf[i] > (char)('A' + 31))
            in_range = false;
    }
    CHECK(in_range, "buffer_randomize_string emits 'A'..'A'+31 characters");
}

static void test_usage_text(void)
{
    static const char *const flags[] = {
        "Usage: wayneko", "--help", "--background-colour", "--outline-colour",
        "--type", "--idle-sleep", "--sleepiness", "--sleepiness-night",
        "--layer", "--follow-pointer", "--survive-close",
    };
    for (size_t i = 0; i < sizeof(flags) / sizeof(flags[0]); i++)
        CHECK(strstr(usage, flags[i]) != NULL,
              "usage text must document '%s'", flags[i]);
}

static void test_defaults(void)
{
    CHECK(animation_timeout == 200, "animation_timeout default is 200ms, got %u",
          (unsigned)animation_timeout);
    CHECK(neko_size == 32, "neko_size default is 32, got %u", (unsigned)neko_size);
    CHECK(max_buffer_multiplicity == 3,
          "max_buffer_multiplicity default is 3, got %d", max_buffer_multiplicity);
    CHECK(sleepiness == 4, "default sleepiness is 4, got %d", sleepiness);
    CHECK(sleepiness_night == 5, "default sleepiness_night is 5, got %d",
          sleepiness_night);
    CHECK(neko_idle_timeout_ms == 180000,
          "default idle timeout is 180000ms, got %u", (unsigned)neko_idle_timeout_ms);
    CHECK(type == NEKO, "default type is NEKO, got %d", (int)type);
    CHECK(follow_pointer == true, "default follow_pointer is true");
    CHECK(layer == ZWLR_LAYER_SHELL_V1_LAYER_BOTTOM,
          "default layer is bottom, got %d", (int)layer);
}

int main(void)
{
    test_colour_from_hex();
    test_get_argument();
    test_colour_from_flag();
    test_atlas();
    test_animation_setters();
    test_movement();
    test_idle_transitions();
    test_hotspot_transitions();
    test_next_state_dispatch();
    test_timespec_diff();
    test_wants_sleep();
    test_buffer_randomize();
    test_usage_text();
    test_defaults();

    printf("wayneko layer-1 behaviour suite: %d passed, %d failed\n",
           g_pass, g_fail);
    if (g_fail != 0) {
        fprintf(stderr, "wayneko layer-1 behaviour suite FAILED\n");
        return 1;
    }
    printf("wayneko layer-1 behaviour suite OK\n");
    return 0;
}
