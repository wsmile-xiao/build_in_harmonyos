/* One consumer case with eight checks: parsing, typed accessors,
 * wrong-type rejection and nested lookup. Owned strings are released. */
#include <toml.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static int failures = 0;
#define CHECK(c, m) do { if (!(c)) { fprintf(stderr, "[FAIL] %s\n", (m)); ++failures; } \
                         else printf("[ok] %s\n", (m)); } while (0)

int main(void) {
    char errbuf[200];
    const char *doc =
        "title = \"tomlc99 probe\"\n"
        "retries = 3\n"
        "ratio = 0.5\n"
        "verbose = true\n"
        "\n[owner]\nname = \"ohpcd\"\n";
    toml_table_t *tab = toml_parse((char *)doc, errbuf, sizeof(errbuf));
    CHECK(tab != NULL, "toml_parse");
    if (!tab) return 1;

    toml_datum_t title = toml_string_in(tab, "title");
    CHECK(title.ok && strcmp(title.u.s, "tomlc99 probe") == 0, "string_in title");
    CHECK(!toml_int_in(tab, "title").ok, "wrong-type int rejected");
    toml_datum_t retries = toml_int_in(tab, "retries");
    CHECK(retries.ok && retries.u.i == 3, "int_in retries");
    toml_datum_t ratio = toml_double_in(tab, "ratio");
    CHECK(ratio.ok && ratio.u.d == 0.5, "double_in ratio");
    toml_datum_t verbose = toml_bool_in(tab, "verbose");
    CHECK(verbose.ok && verbose.u.b, "bool_in verbose");

    toml_table_t *owner = toml_table_in(tab, "owner");
    CHECK(owner != NULL, "table_in owner");
    if (!owner) {
        if (title.ok) free(title.u.s);
        toml_free(tab);
        return 1;
    }
    toml_datum_t name = toml_string_in(owner, "name");
    CHECK(name.ok && strcmp(name.u.s, "ohpcd") == 0, "nested string_in name");

    if (title.ok) free(title.u.s);
    if (name.ok) free(name.u.s);
    toml_free(tab);
    printf("%s: tomlc99 probe (%d failures)\n", failures ? "FAIL" : "PASS", failures);
    return failures ? 1 : 0;
}
