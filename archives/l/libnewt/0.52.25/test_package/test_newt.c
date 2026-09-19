/* Consumer test for libnewt — headless-safe API surface check.
 *
 * newtInit()/newtFinished() and all window/component APIs require a real
 * terminal, so they cannot run in CI. This test instead:
 *  1. links against libnewt (fails at link time if the lib is absent), and
 *  2. reads the exported newtDefaultColorPalette data symbol plus the public
 *     macro/flag surface from newt.h (fails at runtime if data is broken).
 */
#include <stdio.h>
#include <newt.h>

int main(void) {
    int failures = 0;

#define CHECK(cond, label) do { \
    if (cond) { printf("[PASS] %s\n", label); } \
    else { printf("[FAIL] %s\n", label); failures++; } \
} while (0)

    CHECK(newtDefaultColorPalette.rootFg != NULL, "palette rootFg non-NULL");
    CHECK(newtDefaultColorPalette.rootBg != NULL, "palette rootBg non-NULL");
    CHECK(newtDefaultColorPalette.windowFg != NULL, "palette windowFg non-NULL");
    CHECK(newtDefaultColorPalette.buttonBg != NULL, "palette buttonBg non-NULL");
    CHECK(newtDefaultColorPalette.entryFg != NULL, "palette entryFg non-NULL");
    CHECK(newtDefaultColorPalette.textboxBg != NULL, "palette textboxBg non-NULL");

    CHECK(NEWT_COLORSET_ROOT == 2, "NEWT_COLORSET_ROOT == 2");
    CHECK(NEWT_FLAG_RETURNEXIT == (1 << 0), "NEWT_FLAG_RETURNEXIT bit0");
    CHECK(NEWT_FLAG_WRAP == (1 << 6), "NEWT_FLAG_WRAP bit6");
    CHECK(NEWT_FLAG_PASSWORD == (1 << 11), "NEWT_FLAG_PASSWORD bit11");
    CHECK(NEWT_ARG_LAST == -100000, "NEWT_ARG_LAST sentinel");
    CHECK(NEWT_CHECKBOXTREE_SELECTED == '*', "checkboxtree selected glyph");
    CHECK(sizeof(struct newtColors) > 0, "struct newtColors layout");

    if (failures == 0) {
        printf("test_newt: ALL 13 CHECKS PASSED\n");
    } else {
        printf("test_newt: %d CHECK(S) FAILED\n", failures);
    }
    return failures ? 1 : 0;
}
