/* Consumer test for libcacard — exercises the real public API.
 *
 * Only the option-parsing and card-type-mapping entry points are used,
 * so the test needs neither an NSS database nor smart-card hardware:
 *   - vcard_emul_options() parses an emulation argument string
 *   - vcard_emul_type_from_string() maps a card-type name to the enum
 */
#include <stdio.h>

#include <cacard/libcacard.h>

static int checks_total = 0;
static int checks_passed = 0;

#define CHECK(cond, name) \
    do { \
        checks_total++; \
        if (cond) { \
            checks_passed++; \
            printf("ok - %s\n", name); \
        } else { \
            printf("not ok - %s\n", name); \
        } \
    } while (0)

int main(void)
{
    VCardEmulOptions *opts;

    opts = vcard_emul_options("use_hw=no");
    CHECK(opts != NULL, "vcard_emul_options accepts use_hw=no");

    opts = vcard_emul_options("hw_type=CAC");
    CHECK(opts != NULL, "vcard_emul_options accepts hw_type=CAC");

    CHECK(vcard_emul_type_from_string("CAC") == VCARD_EMUL_CAC,
          "CAC maps to VCARD_EMUL_CAC");

    CHECK(vcard_emul_type_from_string("cac") == VCARD_EMUL_CAC,
          "type name match is case-insensitive");

    CHECK(vcard_emul_type_from_string("BOGUS") == VCARD_EMUL_NONE,
          "unknown type maps to VCARD_EMUL_NONE");

    CHECK(vcard_emul_options("bogus_garbage_xyz") == NULL,
          "unknown emulation spec is rejected");

    printf("total=%d passed=%d\n", checks_total, checks_passed);
    return checks_passed == checks_total ? 0 : 1;
}
