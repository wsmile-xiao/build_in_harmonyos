/* test_version.c — version consistency test (based on upstream
 * build-scripts/test-versioning.sh).
 *
 * Verifies that the compiled SDL_ttf version macros match the linked
 * library version, mirroring what test-versioning.sh checks at build
 * time but from the consumer (runtime) perspective.
 */
#include <SDL_ttf.h>
#include <assert.h>

int main(void) {
    /* 1. TTF_Linked_Version returns the runtime library version */
    const SDL_version *v = TTF_Linked_Version();
    assert(v != NULL);

    /* 2. Linked version must match compile-time macros */
    assert(v->major == SDL_TTF_MAJOR_VERSION);
    assert(v->minor == SDL_TTF_MINOR_VERSION);
    assert(v->patch == SDL_TTF_PATCHLEVEL);

    /* 3. Verify exact expected version 2.24.0 */
    assert(v->major == 2);
    assert(v->minor == 24);
    assert(v->patch == 0);

    return 0;
}
