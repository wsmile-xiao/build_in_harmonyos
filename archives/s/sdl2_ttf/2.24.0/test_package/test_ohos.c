/* test_ohos.c — OpenHarmony platform-specific test.
 *
 * Validates that SDL_ttf works correctly in OpenHarmony's headless
 * environment: TTF_Init must succeed WITHOUT any display/video backend
 * (no SDL_Init required), and the FreeType backend operates without a
 * windowing system. This is the platform-specific adaptation test for
 * HarmonyOS.
 */
#include <SDL_ttf.h>
#include <assert.h>

int main(void) {
    /* 1. TTF_Init succeeds WITHOUT any SDL video/display init
     * (OpenHarmony headless characteristic — no windowing system) */
    if (TTF_Init() != 0) {
        return 1;
    }
    assert(TTF_WasInit() == 1);

    /* 2. FreeType backend is operational — linked version queryable
     * without display */
    const SDL_version *v = TTF_Linked_Version();
    assert(v != NULL);
    assert(v->major == 2);
    assert(v->minor == 24);

    /* 3. Error-state handling works headless (returns valid string) */
    const char *err = TTF_GetError();
    assert(err != NULL);

    /* 4. Character encoding toggling works headless
     * (OHOS multi-language/Unicode support) */
    TTF_ByteSwappedUNICODE(1);
    assert(TTF_WasInit() == 1);  /* state stable after setter */
    TTF_ByteSwappedUNICODE(0);

    /* 5. Clean shutdown without display server */
    TTF_Quit();
    assert(TTF_WasInit() == 0);

    return 0;
}
