/* Consumer test for libngf — exercises the bus-free proplist API.
 *
 * Each check prints one "CHECK-OK: <name>" line; the test_package
 * conanfile counts exactly 8 such lines for the HMBS machine-evidence
 * marker. No D-Bus connection is opened (the client API needs a live
 * system bus, absent on OHOS), so every assertion runs offline.
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include <libngf/proplist.h>

static int check_count = 0;

#define CHECK_OK(name) do { printf("CHECK-OK: %s\n", name); check_count++; } while (0)

static void on_entry(const char *key, const void *value, void *userdata)
{
    int *seen = (int *) userdata;
    (void) value;
    if (key != NULL) {
        (*seen)++;
    }
}

int main(void)
{
    NgfProplist *p = NULL;
    NgfProplist *cp = NULL;
    const char *s = NULL;
    int32_t iv = 0;
    uint32_t uv = 0;
    int bv = 0;
    int seen = 0;
    const char **keys = NULL;

    /* 1. string round-trip */
    p = ngf_proplist_new();
    if (p == NULL) {
        return 1;
    }
    if (!ngf_proplist_sets(p, "audio", "/usr/share/sounds/beep.wav")) {
        return 1;
    }
    s = ngf_proplist_gets(p, "audio");
    if (s == NULL || strcmp(s, "/usr/share/sounds/beep.wav") != 0) {
        return 1;
    }
    CHECK_OK("string-roundtrip");

    /* 2. integer round-trip */
    if (!ngf_proplist_set_as_integer(p, "count", -555)) {
        return 1;
    }
    if (!ngf_proplist_get_as_integer(p, "count", &iv) || iv != -555) {
        return 1;
    }
    CHECK_OK("integer-roundtrip");

    /* 3. unsigned round-trip */
    if (!ngf_proplist_set_as_unsigned(p, "level", 555u)) {
        return 1;
    }
    if (!ngf_proplist_get_as_unsigned(p, "level", &uv) || uv != 555u) {
        return 1;
    }
    CHECK_OK("unsigned-roundtrip");

    /* 4. boolean round-trip + value-type queries */
    if (!ngf_proplist_set_as_boolean(p, "enabled", 1)) {
        return 1;
    }
    if (!ngf_proplist_get_as_boolean(p, "enabled", &bv) || bv != 1) {
        return 1;
    }
    if (ngf_proplist_get_value_type(p, "audio") != NGF_PROPLIST_VALUE_TYPE_STRING) {
        return 1;
    }
    if (ngf_proplist_get_value_type(p, "count") != NGF_PROPLIST_VALUE_TYPE_INTEGER) {
        return 1;
    }
    if (ngf_proplist_get_value_type(p, "level") != NGF_PROPLIST_VALUE_TYPE_UNSIGNED) {
        return 1;
    }
    if (ngf_proplist_get_value_type(p, "enabled") != NGF_PROPLIST_VALUE_TYPE_BOOLEAN) {
        return 1;
    }
    CHECK_OK("boolean-and-types");

    /* 5. value parsers */
    if (!ngf_proplist_parse_integer("-555", &iv) || iv != -555) {
        return 1;
    }
    if (!ngf_proplist_parse_unsigned("555", &uv) || uv != 555u) {
        return 1;
    }
    if (!ngf_proplist_parse_boolean("true", &bv) || bv != 1) {
        return 1;
    }
    if (ngf_proplist_parse_boolean("random", &bv) != 0) {
        return 1;
    }
    CHECK_OK("parsers");

    /* 6. iteration */
    ngf_proplist_foreach(p, on_entry, &seen);
    if (seen != 4) {
        return 1;
    }
    CHECK_OK("foreach");

    /* 7. copy preserves all entries */
    cp = ngf_proplist_copy(p);
    if (cp == NULL) {
        return 1;
    }
    s = ngf_proplist_gets(cp, "audio");
    if (s == NULL || strcmp(s, "/usr/share/sounds/beep.wav") != 0) {
        return 1;
    }
    if (!ngf_proplist_get_as_integer(cp, "count", &iv) || iv != -555) {
        return 1;
    }
    CHECK_OK("copy");

    /* 8. key listing */
    keys = ngf_proplist_get_keys(cp);
    if (keys == NULL) {
        return 1;
    }
    {
        int nkeys = 0;
        while (keys[nkeys] != NULL) {
            nkeys++;
        }
        if (nkeys != 4) {
            return 1;
        }
    }
    ngf_proplist_free_keys(keys);
    ngf_proplist_free(cp);
    ngf_proplist_free(p);
    CHECK_OK("keys");

    if (check_count != 8) {
        return 1;
    }
    printf("ALL %d CHECKS PASSED\n", check_count);
    return 0;
}
