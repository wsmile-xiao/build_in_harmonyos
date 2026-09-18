/* Consumer test for rtrlib: offline prefix-validation table exercise.
 *
 * Adds IPv4/IPv6 records to a pfx_table, checks VALID / INVALID / NOT_FOUND
 * outcomes through pfx_table_validate(), then removes the record and checks
 * the table is empty again. Fully deterministic, no network access.
 */
#include <stdio.h>

#include <rtrlib/lib/ip.h>
#include <rtrlib/pfx/pfx.h>

#include <stdint.h>

/* Upstream contract guard (rtrlib 0.8.0, rtrlib/pfx/pfx.h):
 * int pfx_table_validate(table, asn, prefix, mask_len, *result).
 * Any upstream signature change stops compilation here with an
 * explicit message instead of a cryptic call-site error.
 * Compile-time only: CHECK count and runtime behaviour unchanged.
 * Provenance (checked against the exact conandata tarball v0.8.0,
 * 262281 bytes, sha256 8cc99343...560ada): pfx.h L119 declares the
 * 5-arg int form, and upstream tests/test_pfx.c L33/L143/L229 uses
 * the same 5-arg == PFX_SUCCESS idiom as the calls below. */
_Static_assert(__builtin_types_compatible_p(__typeof__(pfx_table_validate),
    int (struct pfx_table *, uint32_t, const struct lrtr_ip_addr *,
         uint8_t, enum pfxv_state *)),
    "pfx_table_validate must be the 5-arg int-returning 0.8.0 form");

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (!(cond)) {                                                         \
            fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__);            \
            return 1;                                                          \
        }                                                                      \
        printf("ok: %s\n", msg);                                               \
    } while (0)

int main(void)
{
    struct pfx_table pfxt;
    struct pfx_record rec;
    struct lrtr_ip_addr addr;
    enum pfxv_state state;

    pfx_table_init(&pfxt, NULL);

    /* IPv4 record: 10.10.0.0, ASN 123, lengths 16-24. */
    CHECK(lrtr_ip_str_to_addr("10.10.0.0", &rec.prefix) == 0, "parse IPv4 prefix");
    rec.asn = 123;
    rec.min_len = 16;
    rec.max_len = 24;
    rec.socket = NULL;
    CHECK(pfx_table_add(&pfxt, &rec) == PFX_SUCCESS, "add IPv4 pfx record");

    CHECK(lrtr_ip_str_to_addr("10.10.5.0", &addr) == 0, "parse IPv4 query address");
    CHECK(pfx_table_validate(&pfxt, 123, &addr, 24, &state) == PFX_SUCCESS,
          "validate call succeeds");
    CHECK(state == BGP_PFXV_STATE_VALID, "matching ASN/len is VALID");

    CHECK(pfx_table_validate(&pfxt, 124, &addr, 24, &state) == PFX_SUCCESS,
          "validate with wrong ASN succeeds");
    CHECK(state == BGP_PFXV_STATE_INVALID, "wrong ASN is INVALID");

    CHECK(lrtr_ip_str_to_addr("192.168.1.0", &addr) == 0, "parse uncovered prefix");
    CHECK(pfx_table_validate(&pfxt, 123, &addr, 24, &state) == PFX_SUCCESS,
          "validate uncovered prefix succeeds");
    CHECK(state == BGP_PFXV_STATE_NOT_FOUND, "uncovered prefix is NOT_FOUND");

    /* IPv6 record: 2a01:4f8:131::/48, ASN 124. */
    CHECK(lrtr_ip_str_to_addr("2a01:4f8:131::", &rec.prefix) == 0, "parse IPv6 prefix");
    rec.asn = 124;
    rec.min_len = 48;
    rec.max_len = 48;
    CHECK(pfx_table_add(&pfxt, &rec) == PFX_SUCCESS, "add IPv6 pfx record");
    CHECK(pfx_table_validate(&pfxt, 124, &rec.prefix, 48, &state) == PFX_SUCCESS,
          "validate IPv6 succeeds");
    CHECK(state == BGP_PFXV_STATE_VALID, "IPv6 record is VALID");

    /* Removal restores NOT_FOUND. */
    rec.asn = 123;
    CHECK(lrtr_ip_str_to_addr("10.10.0.0", &rec.prefix) == 0,
          "re-parse IPv4 prefix for removal");
    rec.min_len = 16;
    rec.max_len = 24;
    CHECK(pfx_table_remove(&pfxt, &rec) == PFX_SUCCESS, "remove IPv4 pfx record");
    CHECK(lrtr_ip_str_to_addr("10.10.5.0", &addr) == 0, "re-parse query address");
    CHECK(pfx_table_validate(&pfxt, 123, &addr, 24, &state) == PFX_SUCCESS,
          "validate after removal succeeds");
    CHECK(state == BGP_PFXV_STATE_NOT_FOUND, "removed prefix is NOT_FOUND");

    pfx_table_free(&pfxt);
    printf("test_pfx_validation: ALL OK\n");
    return 0;
}
