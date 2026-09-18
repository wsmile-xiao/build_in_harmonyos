#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <igloo/igloo.h>
#include <igloo/error.h>
#include <igloo/ro.h>
#include <igloo/sp.h>
#include <igloo/tap.h>
#include <igloo/uuid.h>

/* Real consumer test (R34): links against the packaged libigloo and
 * exercises its public API surface — library initialization, version
 * reporting, string pool ref/unref, UUID generation/validation and the
 * TAP mini-framework the library itself ships. Exits non-zero on any
 * failed assertion. This is not a print-only stub. */
int main(void) {
    int fails = 0;
    igloo_ro_t instance = igloo_RO_NULL;
    const char *version = NULL;
    int major = -1, minor = -1, patch = -1;

    /* 1. initialize the library (required before sp/uuid usage) */
    if (igloo_initialize(&instance) != igloo_ERROR_NONE) {
        printf("consumer test: igloo_initialize FAILED\n");
        return 1;
    }

    /* 2. version reporting must match the packaged 0.9.5 */
    if (igloo_version_get(&version, &major, &minor, &patch) != igloo_ERROR_NONE
        || !version || major != 0 || minor != 9 || patch != 5) {
        printf("consumer test: igloo_version_get FAILED (v=%s %d.%d.%d)\n",
               version ? version : "(null)", major, minor, patch);
        igloo_ro_unref(&instance);
        return 1;
    }

    /* 3. version compatibility check used by embedding applications
     *    (docs: "Typical calls set all max_* parameters to -1") */
    if (!igloo_version_check(0, 9, 0, -1, -1, -1)) {
        printf("consumer test: igloo_version_check FAILED\n");
        igloo_ro_unref(&instance);
        return 1;
    }

    /* 4. string pool: immutable reference create + unref round trip */
    {
        const char *ref = NULL;
        if (igloo_sp_replace("libigloo-consumer-test", &ref, instance) != igloo_ERROR_NONE
            || !ref || strcmp(ref, "libigloo-consumer-test") != 0) {
            printf("consumer test: igloo_sp_replace FAILED\n");
            igloo_ro_unref(&instance);
            return 1;
        }
        if (igloo_sp_unref(&ref, instance) != igloo_ERROR_NONE || ref != NULL) {
            printf("consumer test: igloo_sp_unref FAILED\n");
            igloo_ro_unref(&instance);
            return 1;
        }
    }

    /* 5. UUID v4 generation (exercises prng + sp on OHOS) and validation */
    {
        char *uuid = NULL;
        if (igloo_uuid_new_random_cstr(&uuid, instance) != igloo_ERROR_NONE || !uuid) {
            printf("consumer test: igloo_uuid_new_random_cstr FAILED\n");
            igloo_ro_unref(&instance);
            return 1;
        }
        if (strlen(uuid) != 36
            || igloo_uuid_is_valid(uuid, igloo_UUID_STRICTNESS_STRICT) != igloo_ERROR_NONE) {
            printf("consumer test: generated UUID invalid: %s\n", uuid);
            free(uuid);
            igloo_ro_unref(&instance);
            return 1;
        }
        /* strict validator must reject a malformed UUID (group length) —
         * same fixture as upstream tests/uuid.c, expects igloo_ERROR_ILLSEQ */
        if (igloo_uuid_is_valid("551a9547-fe63-4cf-a153-2801bac47ff8",
                                igloo_UUID_STRICTNESS_STRICT) == igloo_ERROR_NONE) {
            printf("consumer test: igloo_uuid_is_valid accepted malformed input\n");
            free(uuid);
            igloo_ro_unref(&instance);
            return 1;
        }
        free(uuid);
    }

    /* 6. the TAP mini-framework the library exposes to consumers.
     * Note: get_stats is evaluated as an argument BEFORE tap_test_success
     * records its own assertion, so the snapshot reflects the first two. */
    {
        igloo_tap_stats_t stats;
        igloo_tap_init();
        igloo_tap_test("consumer tap works", true);
        igloo_tap_test("consumer tap second assert", true);
        igloo_tap_test_success("consumer tap stats", igloo_tap_get_stats(&stats));
        if (stats.count != 2 || stats.passed != 2 || stats.failed != 0) {
            printf("consumer test: tap stats mismatch (%d/%d/%d)\n",
                   (int)stats.count, (int)stats.passed, (int)stats.failed);
            fails++;
        }
        igloo_tap_fin();
    }

    /* 7. release the instance the upstream way (igloo_ro_unref) */
    if (igloo_ro_unref(&instance) != igloo_ERROR_NONE || !igloo_ro_is_null(instance)) {
        printf("consumer test: igloo_ro_unref FAILED\n");
        return 1;
    }

    printf("consumer test libigloo 0.9.5: PASS (version %s)\n", version);
    return fails ? 1 : 0;
}
