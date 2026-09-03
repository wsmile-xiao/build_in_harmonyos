#include <stringzilla/stringzilla.h>

#include <stddef.h>
int main(void) {
    const char haystack[] = "HarmonyOS StringZilla";
    const char needle[] = "String";
    const char missing[] = "missing";
    const size_t haystack_length = sizeof(haystack) - 1;
    const size_t needle_length = sizeof(needle) - 1;
    const size_t missing_length = sizeof(missing) - 1;

    if (sz_find(haystack, haystack_length, needle, needle_length) != haystack + 10) {
        return 1;
    }
    if (sz_find_byte(haystack, haystack_length, "O") != haystack + 7) {
        return 2;
    }
    if (sz_find(haystack, haystack_length, missing, missing_length) != NULL) {
        return 3;
    }
    return sz_equal("abc", "abc", 3) && !sz_equal("abc", "abd", 3) ? 0 : 4;
}
