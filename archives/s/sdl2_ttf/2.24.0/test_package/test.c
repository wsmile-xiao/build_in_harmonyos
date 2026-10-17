/* test_sdl2_ttf — consumer-side functional test for sdl2_ttf.
 *
 * Upstream ships no automated test suite (ctest/make check). showfont.c /
 * glfont.c are interactive sample programs that need a display + font file.
 * This test exercises the core TTF API lifecycle without a display or font
 * file, so it runs in headless CI.
 */
#include <SDL_ttf.h>
#include <assert.h>
#include <string.h>

int main(void) {
    /* 1. TTF_Init — must succeed (initializes the FreeType backend) */
    if (TTF_Init() != 0) {
        return 1;
    }

    /* 2. TTF_WasInit — should report initialized (1) */
    assert(TTF_WasInit() == 1);

    /* 3. TTF_Linked_Version — verify the linked library reports 2.24.x */
    const SDL_version *v = TTF_Linked_Version();
    assert(v != NULL);
    assert(v->major == 2);
    assert(v->minor == 24);
    assert(v->patch == 0);

    /* 4. TTF_ByteSwappedUNICODE — setter, no return; just must not crash */
    TTF_ByteSwappedUNICODE(0);

    /* 5. TTF_GetError — string API reachable (returns "" when no error set) */
    const char *err = TTF_GetError();
    assert(err != NULL);

    /* 6. TTF_Quit — clean shutdown */
    TTF_Quit();

    /* 7. After quit, TTF_WasInit reports 0 */
    assert(TTF_WasInit() == 0);

    return 0;
}
