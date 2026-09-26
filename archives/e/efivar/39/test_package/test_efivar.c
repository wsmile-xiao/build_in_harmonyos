/* test_efivar.c — Consumer test for efivar/39
 *
 * Links against libefivar and exercises core API functions:
 *   1. efi_get_libefivar_version() — returns the compiled-in library version
 *   2. efi_str_to_guid() — parses a well-known GUID string
 *   3. efi_guid_is_empty() — validates the parsed GUID is non-zero
 *   4. efi_guid_to_str() — formats the GUID back to canonical string form
 *   5. efi_guid_cmp() — GUID equality round-trip
 */
#include <stdio.h>
#include <string.h>
#include <efivar.h>

int main(void)
{
    int failures = 0;

    /* 1. Verify the library reports a non-zero version */
    uint32_t version = efi_get_libefivar_version();
    if (version == 0) {
        fprintf(stderr, "FAIL: efi_get_libefivar_version returned 0\n");
        failures++;
    } else {
        printf("libefivar version: %u.%u\n",
               (version >> 8) & 0xff, version & 0xff);
    }

    /* 2. Parse a well-known GUID string */
    efi_guid_t guid;
    int ret = efi_str_to_guid("12345678-1234-1234-1234-123456789abc", &guid);
    if (ret != 0) {
        fprintf(stderr, "FAIL: efi_str_to_guid returned %d\n", ret);
        failures++;
    }

    /* 3. The parsed GUID must not be zero */
    if (efi_guid_is_empty(&guid)) {
        fprintf(stderr, "FAIL: parsed GUID is unexpectedly zero\n");
        failures++;
    }

    /* 4. Format the GUID back to canonical text and compare.
     * efi_guid_to_str returns the number of characters written (36 for a
     * canonical GUID), not 0, on success. */
    char *str = NULL;
    ret = efi_guid_to_str(&guid, &str);
    if (ret != 36 || str == NULL) {
        fprintf(stderr, "FAIL: efi_guid_to_str returned %d (expected 36)\n", ret);
        failures++;
    } else if (strcmp(str, "12345678-1234-1234-1234-123456789abc") != 0) {
        fprintf(stderr, "FAIL: GUID round-trip mismatch: %s\n", str);
        failures++;
    } else {
        printf("GUID round-trip: %s\n", str);
    }

    /* 5. efi_guid_cmp on identical GUIDs must be 0 */
    efi_guid_t guid2;
    efi_str_to_guid("12345678-1234-1234-1234-123456789abc", &guid2);
    if (efi_guid_cmp(&guid, &guid2) != 0) {
        fprintf(stderr, "FAIL: efi_guid_cmp on identical GUIDs != 0\n");
        failures++;
    }

    if (failures) {
        fprintf(stderr, "efivar consumer test: %d assertion(s) FAILED\n", failures);
        return 1;
    }
    printf("efivar API test: all 5 assertions passed\n");
    return 0;
}
