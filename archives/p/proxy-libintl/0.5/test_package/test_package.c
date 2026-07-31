#include <libintl.h>

#include <stdio.h>
#include <string.h>

static int expect_string(const char *label, const char *actual, const char *expected)
{
    if (actual == NULL || strcmp(actual, expected) != 0) {
        fprintf(stderr, "FAIL %s expected=%s actual=%s\n",
                label, expected, actual == NULL ? "<null>" : actual);
        return 1;
    }
    return 0;
}

int main(void)
{
    int failures = 0;

    failures += expect_string("gettext", gettext("hello"), "hello");
    failures += expect_string("ngettext-one", ngettext("item", "items", 1), "item");
    failures += expect_string("ngettext-many", ngettext("item", "items", 2), "items");
    failures += expect_string("default-domain", textdomain(NULL), "messages");
    failures += expect_string("set-domain", textdomain("proxy-test"), "proxy-test");
    failures += expect_string("current-domain", textdomain(NULL), "proxy-test");
    failures += expect_string(
        "bind-directory", bindtextdomain("proxy-test", "/unused"), "/dummy"
    );
    failures += expect_string(
        "codeset", bind_textdomain_codeset("proxy-test", "UTF-8"), "UTF-8"
    );

    if (failures != 0) {
        return 1;
    }

    puts("PASS proxy-libintl consumer flows=1 internal_checks=8");
    return 0;
}
