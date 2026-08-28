#include <stdlib.h>
#include <string.h>

#include <klib/khash.h>
#include <klib/kstring.h>

KHASH_MAP_INIT_STR(words, int)

int main(void)
{
    int inserted = 0;
    int result = 1;
    khint_t key;
    khash_t(words) *table = kh_init(words);
    kstring_t text = {0, 0, NULL};

    if (table == NULL)
        return 1;
    key = kh_put(words, table, "harmony", &inserted);
    if (inserted <= 0)
        goto cleanup;
    kh_value(table, key) = 42;
    key = kh_get(words, table, "harmony");
    if (key == kh_end(table) || kh_value(table, key) != 42)
        goto cleanup;

    if (kputs("Harmony", &text) < 0)
        goto cleanup;
    if (kputc('O', &text) < 0)
        goto cleanup;
    if (kputs("S", &text) < 0)
        goto cleanup;
    if (strcmp(text.s, "HarmonyOS") != 0)
        goto cleanup;

    result = 0;

cleanup:
    free(text.s);
    kh_destroy(words, table);
    return result;
}
