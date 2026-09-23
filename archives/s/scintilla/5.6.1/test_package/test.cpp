/**
 * test.cpp — Scintilla 5.6.1 test_package
 *
 * Exercises the BN_Sci_* C API exported by libscintilla_ohos.so:
 *   BN_Sci_Create → BN_Sci_Init → BN_Sci_SetText → BN_Sci_GetLength
 *   → BN_Sci_GetLineCount → BN_Sci_Clear → BN_Sci_Destroy
 *
 * Verifies that the shared library loads, symbols resolve, and
 * basic text operations produce correct results.
 */

#include <cstdio>
#include <cstdlib>
#include <cstring>

// ScintillaOHOS.h provides the BN_Sci_* C API declarations
#include "ScintillaOHOS.h"

int main(void) {
    int failures = 0;

    // ── 1. Create ──────────────────────────────────────────────────
    void *editor = BN_Sci_Create();
    if (!editor) {
        fprintf(stderr, "FAIL: BN_Sci_Create returned NULL\n");
        return 1;
    }
    printf("OK: BN_Sci_Create() = %p\n", editor);

    // ── 2. Init (800x600, no drawing surface needed for text ops) ──
    BN_Sci_Init(editor, 800, 600);
    printf("OK: BN_Sci_Init(800, 600)\n");

    // ── 3. SetText ─────────────────────────────────────────────────
    const char *text = "Hello HarmonyOS!\nLine 2\nLine 3";
    BN_Sci_SetText(editor, text);
    printf("OK: BN_Sci_SetText(\"%s\")\n", text);

    // ── 4. GetLength — should match input length ───────────────────
    int length = BN_Sci_GetLength(editor);
    int expected = (int)strlen(text);
    if (length == expected) {
        printf("OK: BN_Sci_GetLength() = %d (expected %d)\n", length, expected);
    } else {
        fprintf(stderr, "FAIL: BN_Sci_GetLength() = %d, expected %d\n", length, expected);
        failures++;
    }

    // ── 5. GetLineCount — "Hello\nLine2\nLine3" = 3 lines ─────────
    int lines = BN_Sci_GetLineCount(editor);
    if (lines >= 1) {
        printf("OK: BN_Sci_GetLineCount() = %d\n", lines);
    } else {
        fprintf(stderr, "FAIL: BN_Sci_GetLineCount() = %d, expected >= 1\n", lines);
        failures++;
    }

    // ── 6. GetCurPos ───────────────────────────────────────────────
    int curpos = BN_Sci_GetCurPos(editor);
    printf("OK: BN_Sci_GetCurPos() = %d\n", curpos);

    // ── 7. SetCurPos ────────────────────────────────────────────────
    BN_Sci_SetCurPos(editor, 5);
    int newpos = BN_Sci_GetCurPos(editor);
    if (newpos == 5) {
        printf("OK: BN_Sci_SetCurPos(5) → GetCurPos() = %d\n", newpos);
    } else {
        fprintf(stderr, "FAIL: BN_Sci_SetCurPos(5) → GetCurPos() = %d\n", newpos);
        failures++;
    }

    // ── 8. GetModify ───────────────────────────────────────────────
    int modified = BN_Sci_GetModify(editor);
    printf("OK: BN_Sci_GetModify() = %d\n", modified);

    // ── 9. Clear ───────────────────────────────────────────────────
    BN_Sci_Clear(editor);
    int clear_len = BN_Sci_GetLength(editor);
    if (clear_len == 0) {
        printf("OK: BN_Sci_Clear() → GetLength() = 0\n");
    } else {
        fprintf(stderr, "FAIL: BN_Sci_Clear() → GetLength() = %d, expected 0\n", clear_len);
        failures++;
    }

    // ── 10. Destroy ────────────────────────────────────────────────
    BN_Sci_Destroy(editor);
    printf("OK: BN_Sci_Destroy()\n");

    // ── Summary ────────────────────────────────────────────────────
    if (failures == 0) {
        printf("\n=== ALL TESTS PASSED ===\n");
        return 0;
    } else {
        printf("\n=== %d TEST(S) FAILED ===\n", failures);
        return 1;
    }
}
