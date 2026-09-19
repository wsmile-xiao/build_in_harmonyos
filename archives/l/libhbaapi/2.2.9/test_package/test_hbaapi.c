/*
 * Consumer test for the installed libHBAAPI package.
 *
 * Uses only the public headers and the installed shared library: the API
 * version constant, library load/unload and the deterministic "no vendor
 * library configured" behaviour (zero adapters, adapter lookup rejected).
 */
#include <stdio.h>
#include <string.h>
#include <time.h> /* hbaapi.h uses struct tm without including <time.h> */

#include <hbaapi.h>

static int failures = 0;

#define CHECK(condition, message)                                        \
    do {                                                                 \
        if (condition) {                                                 \
            printf("  ok   %s\n", message);                              \
        } else {                                                         \
            printf("  FAIL %s\n", message);                              \
            failures++;                                                  \
        }                                                                \
    } while (0)

int main(void)
{
    HBA_STATUS status;
    HBA_UINT32 adapters;
    char name[256];

    printf("libhbaapi consumer test\n");

    /* --- version ------------------------------------------------------- */
    CHECK(HBA_GetVersion() == (HBA_UINT32)HBA_LIBVERSION,
          "HBA_GetVersion matches the header's HBA_LIBVERSION");

    /* --- library lifecycle -------------------------------------------- */
    status = HBA_LoadLibrary();
    printf("  info HBA_LoadLibrary -> %d\n", (int)status);
    CHECK(status == HBA_STATUS_OK || status == HBA_STATUS_ERROR,
          "HBA_LoadLibrary returns a defined status");

    /* --- no vendor library is configured ------------------------------ */
    adapters = HBA_GetNumberOfAdapters();
    printf("  info HBA_GetNumberOfAdapters -> %u\n", (unsigned)adapters);
    CHECK(adapters == 0, "no vendor library means zero adapters");

    memset(name, 0, sizeof name);
    status = HBA_GetAdapterName(0, name);
    CHECK(status != HBA_STATUS_OK,
          "adapter 0 lookup is rejected when no adapter exists");

    /* --- refresh and shutdown ----------------------------------------- */
    HBA_RefreshAdapterConfiguration();
    CHECK(HBA_GetNumberOfAdapters() == 0,
          "refresh keeps the adapter count at zero");

    status = HBA_FreeLibrary();
    CHECK(status == HBA_STATUS_OK || status == HBA_STATUS_ERROR,
          "HBA_FreeLibrary returns a defined status");

    printf("consumer assertions: %d failed\n", failures);
    return failures == 0 ? 0 : 1;
}
