/*
 * test_package consumer test — sili 0.3.0
 *
 * Consumer-view validation (R34/PF3): links the installed static library
 * `libsili.a`, includes the installed public header `sili.h` (no private
 * headers), and calls public APIs with observable results:
 *   - si_stringEqual / siString (string equality)
 *   - si_stringFromCStr (C-string conversion)
 *   - si_stringTrim (whitespace trimming)
 *   - si_stringUpper / si_stringLower (case conversion)
 *   - si_printfLn (print API)
 * The binary exits 0 only if every check holds.
 */
#define SI_IMPLEMENTATION 1
#include <sili.h>

#include <stdio.h>

int main(void) {
    /* String construction + equality over public API. */
    siString a = SI_STR("harmony");
    siString b = SI_STR("harmony");
    if (!si_stringEqual(a, b)) {
        si_printfLn("FAIL: si_stringEqual(a, b)");
        return 1;
    }

    siString c = SI_STR("harmonyos-pc");
    if (si_stringEqual(a, c)) {
        si_printfLn("FAIL: unequal strings reported equal");
        return 1;
    }

    /* C-string conversion with observable length. */
    siAllocator alloc = si_allocatorHeap();
    siString conv = si_stringFromCStr("harmony", alloc);
    if (conv.len != 7 || !si_stringEqual(conv, SI_STR("harmony"))) {
        si_printfLn("FAIL: si_stringFromCStr length/content");
        return 1;
    }

    /* Whitespace trimming of "  hi  " -> "hi". */
    siString trimmed = si_stringTrim(SI_STR("  hi  "), SI_STR(" "));
    if (!si_stringEqual(trimmed, SI_STR("hi"))) {
        si_printfLn("FAIL: si_stringTrim");
        return 1;
    }

    /* Case conversion: "Ohos" -> upper "OHOS", lower "ohos". */
    siString up = si_stringUpper(SI_STR("Ohos"), alloc);
    if (!si_stringEqual(up, SI_STR("OHOS"))) {
        si_printfLn("FAIL: si_stringUpper");
        return 1;
    }
    siString low = si_stringLower(SI_STR("OHOS"), alloc);
    if (!si_stringEqual(low, SI_STR("ohos"))) {
        si_printfLn("FAIL: si_stringLower");
        return 1;
    }

    si_printfLn("test_sili: all consumer checks passed");
    printf("sili consumer test OK\n");
    return 0;
}
