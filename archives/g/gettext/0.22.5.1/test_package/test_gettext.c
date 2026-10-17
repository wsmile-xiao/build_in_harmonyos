#include <libintl.h>
#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    const char *domain = "gettext-conan-test";
    const char *message = "missing-message";

    if (argc != 2) {
        return 1;
    }
    if (setlocale(LC_ALL, "C.UTF-8") == NULL &&
        setlocale(LC_ALL, "zh_CN.UTF-8") == NULL &&
        setlocale(LC_ALL, "") == NULL) {
        return 2;
    }
    if (setenv("LANGUAGE", "zh_CN", 1) != 0) {
        return 3;
    }
    if (bindtextdomain(domain, argv[1]) == NULL) {
        return 4;
    }
    if (bind_textdomain_codeset(domain, "UTF-8") == NULL) {
        return 5;
    }
    if (textdomain(domain) == NULL) {
        return 6;
    }
    if (strcmp(gettext("hello"), "\xe4\xbd\xa0\xe5\xa5\xbd") != 0) {
        return 7;
    }
    if (strcmp(dgettext(domain, message), message) != 0) {
        return 8;
    }
    if (strcmp(ngettext("apple", "apples", 1), "\xe8\x8b\xb9\xe6\x9e\x9c") != 0) {
        return 9;
    }
    if (strcmp(ngettext("apple", "apples", 2), "\xe8\x8b\xb9\xe6\x9e\x9c\xe4\xbb\xac") != 0) {
        return 10;
    }

    printf("gettext libintl consumer passed\n");
    return 0;
}
