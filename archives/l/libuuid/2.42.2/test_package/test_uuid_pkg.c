/* test_uuid_pkg.c - exercise the packaged libuuid API (offline, no root, no
 * uuidd daemon, no /dev/urandom assumption beyond uuid_generate).
 *
 * Covers the public API surface: uuid_generate / uuid_unparse_lower /
 * uuid_parse / uuid_compare / uuid_is_null / uuid_clear / uuid_type /
 * uuid_variant / uuid_time (v1) and the predefined namespace templates
 * (uuid_get_template / uuid_generate_md5+sha1 via UUIDS_TYPE constants).
 */
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <uuid/uuid.h>

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); failures++; } \
    else { printf("ok: %s\n", msg); } \
} while (0)

int main(void)
{
    uuid_t uuid, uuid2, ns;
    char str[UUID_STR_LEN + 1];

    /* 1. generate a random (v4) UUID */
    uuid_generate(uuid);
    uuid_unparse_lower(uuid, str);
    CHECK(strlen(str) == 36, "uuid_generate + uuid_unparse_lower produce 36-char string");
    /* v4: version nibble 4, variant 8/9/a/b */
    CHECK((uuid[6] >> 4) == 4, "random UUID has version 4");
    CHECK((uuid[8] >> 6) == 2, "random UUID has RFC 4122 variant");

    /* 2. parse round trip */
    CHECK(uuid_parse(str, uuid2) == 0, "uuid_parse accepts generated string");
    CHECK(uuid_compare(uuid, uuid2) == 0, "uuid_compare round trip equal");

    /* 3. is_null / clear */
    CHECK(!uuid_is_null(uuid), "uuid_is_null false for generated uuid");
    uuid_clear(uuid);
    CHECK(uuid_is_null(uuid), "uuid_is_null true after uuid_clear");

    /* 4. type / variant accessors */
    uuid_generate(uuid);
    CHECK(uuid_type(uuid) == UUID_TYPE_DCE_RANDOM, "uuid_type == UUID_TYPE_DCE_RANDOM (4)");
    CHECK(uuid_variant(uuid) == UUID_VARIANT_DCE, "uuid_variant == UUID_VARIANT_DCE");

    /* 5. namespace templates (uuid_get_template) */
    CHECK(uuid_parse("6ba7b810-9dad-11d1-80b4-00c04fd430c8", ns) == 0, "parse dns namespace uuid");
    CHECK(uuid_compare(ns, *uuid_get_template("dns")) == 0, "uuid_get_template(dns) matches RFC 4122 value");
    CHECK(uuid_get_template("no-such-namespace") == NULL, "uuid_get_template(unknown) returns NULL");
    CHECK(uuid_get_template(NULL) == NULL, "uuid_get_template(NULL) returns NULL");

    /* 6. v1 time-based UUID: uuid_time and uuid_type */
    uuid_generate_time(uuid);
    uuid_unparse_lower(uuid, str);
    CHECK(uuid_type(uuid) == UUID_TYPE_DCE_TIME, "uuid_generate_time gives v1 (time-based)");
    CHECK((uuid[6] >> 4) == 1, "v1 UUID has version nibble 1");
    {
        time_t t = uuid_time(uuid, NULL);
        struct tm tmv;
        time_t now = time(NULL);
        gmtime_r(&t, &tmv);
        CHECK(t > 0 && (now - t) < 86400 * 365, "uuid_time within the last year (v1 timestamp)");
        CHECK(tmv.tm_year + 1900 >= 2026, "uuid_time gregorian year >= 2026");
    }

    /* 7. md5/sha1 namespace-based generation (UUIDS_TYPE constants) */
    uuid_generate_md5(uuid, *uuid_get_template("dns"), "www.widgets.com", strlen("www.widgets.com"));
    CHECK(uuid_type(uuid) == UUID_TYPE_DCE_MD5, "uuid_generate_md5 gives v3 (md5)");
    uuid_generate_sha1(uuid, *uuid_get_template("dns"), "www.widgets.com", strlen("www.widgets.com"));
    CHECK(uuid_type(uuid) == UUID_TYPE_DCE_SHA1, "uuid_generate_sha1 gives v5 (sha1)");

    if (failures) {
        fprintf(stderr, "%d failures\n", failures);
        return 1;
    }
    printf("PASS: libuuid API smoke test\n");
    return 0;
}
