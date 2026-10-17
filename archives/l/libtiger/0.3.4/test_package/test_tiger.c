/* Consumer test for libtiger — exercises the real public API.
 *
 * Normal scenario: version queries plus a full renderer lifecycle
 * (create, clear color, cairo image buffer binding, dirty check, render
 * with output verification, destroy). Rendering a cleared frame needs no
 * fonts, so it runs headless on HarmonyOS.
 *
 * Fault-injection scenario (--null-args): NULL arguments must return
 * TIGER_E_INVALID_PARAMETER instead of crashing.
 *
 * Every check prints exactly one PASS line; the test_package harness
 * counts PASS lines as the discovered/passed evidence.
 */

#include <stdio.h>
#include <string.h>

#include <tiger/tiger.h>

#define CHECK(cond, name)                                                     \
    do {                                                                      \
        if (!(cond)) {                                                        \
            fprintf(stderr, "FAIL: %s\n", name);                               \
            return 1;                                                         \
        }                                                                     \
        printf("PASS: %s\n", name);                                           \
    } while (0)

static int run_normal(void)
{
    tiger_renderer *tr = NULL;
    static unsigned char buf[64 * 48 * 4];

    memset(buf, 0, sizeof(buf));

    CHECK(strcmp(tiger_get_version_string(), "libtiger 0.3.4") == 0,
          "version-string");
    CHECK(tiger_get_version() == 0x000304, "version-number");
    CHECK(TIGER_VERSION_MAJOR == 0 && TIGER_VERSION_MINOR == 3 &&
          TIGER_VERSION_PATCH == 4, "version-macros");
    CHECK(tiger_renderer_create(&tr) == 0 && tr != NULL, "renderer-create");
    CHECK(tiger_renderer_set_surface_clear_color(tr, 1, 1.0, 1.0, 1.0, 1.0) == 0,
          "clear-color");
    CHECK(tiger_renderer_set_buffer(tr, buf, 64, 48, 64 * 4, 0) == 0,
          "set-buffer");
    CHECK(tiger_renderer_is_dirty(tr) != 0, "is-dirty");
    CHECK(tiger_renderer_render(tr) == 0, "render");
    CHECK(buf[0] != 0, "buffer-filled");
    CHECK(tiger_renderer_destroy(tr) == 0, "renderer-destroy");
    return 0;
}

static int run_null_args(void)
{
    tiger_renderer *tr = NULL;
    static unsigned char buf[16 * 16 * 4];

    CHECK(tiger_renderer_create(NULL) == TIGER_E_INVALID_PARAMETER,
          "create-null");
    CHECK(tiger_renderer_destroy(NULL) == TIGER_E_INVALID_PARAMETER,
          "destroy-null");
    CHECK(tiger_renderer_render(NULL) == TIGER_E_INVALID_PARAMETER,
          "render-null");
    CHECK(tiger_renderer_create(&tr) == 0 && tr != NULL, "recreate");
    CHECK(tiger_renderer_set_buffer(tr, NULL, 16, 16, 16 * 4, 0) ==
          TIGER_E_INVALID_PARAMETER, "buffer-null-ptr");
    CHECK(tiger_renderer_set_buffer(NULL, buf, 16, 16, 16 * 4, 0) ==
          TIGER_E_INVALID_PARAMETER, "buffer-null-renderer");
    CHECK(tiger_renderer_destroy(tr) == 0, "final-destroy");
    return 0;
}

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "--null-args") == 0)
        return run_null_args();
    if (argc != 1) {
        fprintf(stderr, "usage: test_tiger [--null-args]\n");
        return 2;
    }
    return run_normal();
}
