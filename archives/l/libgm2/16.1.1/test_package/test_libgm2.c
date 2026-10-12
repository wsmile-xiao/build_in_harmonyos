/* Consumer test for the packaged libgm2 runtime libraries.
 *
 * Links against libm2iso / libm2pim (plus the packaged libstdc++.a stub
 * which provides the C++ exception runtime symbols referenced by
 * libm2pim) and calls real Modula-2 runtime APIs exported with a C
 * calling convention.
 */
#include <stdio.h>

/* libm2pim: PIM-style string helpers (C-callable). */
extern unsigned long m2pim_Builtins_strlen(const char *);
extern int m2pim_Builtins_strcmp(const char *, const char *);

/* libm2iso: ISO-style character classification. */
extern int m2iso_CharClass_IsLetter(int);
extern int m2iso_CharClass_IsNumeric(int);
extern int m2iso_CharClass_IsUpper(int);

int main(void)
{
    const char *hello = "libgm2";

    if (m2pim_Builtins_strlen(hello) != 6U) {
        return 1; /* runtime strlen broken */
    }
    if (m2pim_Builtins_strcmp("abc", "abd") >= 0) {
        return 2; /* runtime strcmp ordering broken */
    }
    if (m2pim_Builtins_strcmp("abc", "abc") != 0) {
        return 3; /* runtime strcmp equality broken */
    }
    if (!m2iso_CharClass_IsLetter('A')) {
        return 4; /* letter classification broken */
    }
    if (m2iso_CharClass_IsLetter('7')) {
        return 5; /* digit misclassified as letter */
    }
    if (!m2iso_CharClass_IsNumeric('7')) {
        return 6; /* digit classification broken */
    }
    if (!m2iso_CharClass_IsUpper('A') || m2iso_CharClass_IsUpper('a')) {
        return 7; /* case classification broken */
    }
    puts("libgm2-ohos-ok");
    return 0;
}
