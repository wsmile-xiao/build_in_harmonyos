#include <p11-kit/p11-kit.h>
#include <p11-kit/uri.h>
#include <p11-kit/version.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(condition)                                                       \
    do {                                                                       \
        if (!(condition)) {                                                    \
            fprintf(stderr, "check failed at line %d: %s\n", __LINE__,      \
                    #condition);                                               \
            return 1;                                                          \
        }                                                                      \
    } while (0)

int main(void) {
    static const char expected_label[] = "Test Label";
    P11KitUri *uri = NULL;
    CK_ATTRIBUTE_PTR label = NULL;
    char *formatted = NULL;

    CHECK(P11_KIT_CHECK_VERSION(0, 26, 2));
    CHECK(p11_kit_check_version(0, 26, 2) == 1);
    CHECK(p11_kit_check_version(0, 26, 3) == 0);

    uri = p11_kit_uri_new();
    CHECK(uri != NULL);
    CHECK(p11_kit_uri_parse("pkcs11:object=Test%20Label;type=cert",
                            P11_KIT_URI_FOR_ANY, uri) == P11_KIT_URI_OK);

    label = p11_kit_uri_get_attribute(uri, CKA_LABEL);
    CHECK(label != NULL);
    CHECK(label->ulValueLen == sizeof(expected_label) - 1);
    CHECK(memcmp(label->pValue, expected_label, sizeof(expected_label) - 1) == 0);

    CHECK(p11_kit_uri_format(uri, P11_KIT_URI_FOR_ANY, &formatted) ==
          P11_KIT_URI_OK);
    CHECK(formatted != NULL);
    CHECK(strstr(formatted, "object=Test%20Label") != NULL);

    free(formatted);
    p11_kit_uri_free(uri);
    puts("p11-kit consumer checks passed: 11");
    return 0;
}
