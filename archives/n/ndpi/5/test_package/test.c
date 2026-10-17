/* test_ndpi.c — Conan L1 consumer test for ndpi/5.
 *
 * Exercises the real public API the way a downstream DPI application would:
 * create a detection module, finalize it, then query the protocol database
 * (count, well-known names) and core helpers (flow struct size, revision).
 * Every check below is a genuine assertion against the linked library;
 * a stub that never touches libndpi cannot pass.
 */
#include <ndpi/ndpi_api.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    int errors = 0;
    int passed = 0;

    /* 1. A detection module can be created. */
    struct ndpi_detection_module_struct *mod = ndpi_init_detection_module(NULL);
    if (mod == NULL) {
        fprintf(stderr, "FAIL: ndpi_init_detection_module returned NULL\n");
        errors++;
    } else {
        printf("OK: detection module created\n");
        passed++;
    }
    if (mod == NULL)
        goto summary;

    /* 2. Initialization finalizes cleanly (loads dissectors, ports). */
    if (ndpi_finalize_initialization(mod) != 0) {
        fprintf(stderr, "FAIL: ndpi_finalize_initialization != 0\n");
        errors++;
    } else {
        printf("OK: initialization finalized\n");
        passed++;
    }

    /* 3. The protocol database is populated (nDPI 5 ships hundreds). */
    {
        unsigned int n = ndpi_get_num_protocols(mod);
        printf("OK: num_protocols = %u\n", n);
        if (n < 100) {
            fprintf(stderr, "FAIL: suspiciously few protocols: %u\n", n);
            errors++;
        } else {
            passed++;
        }
    }

    /* 4. Well-known id 7 resolves to HTTP. */
    {
        char *name = ndpi_get_proto_name(mod, NDPI_PROTOCOL_HTTP);
        printf("OK: proto 7 name = %s\n", name ? name : "(null)");
        if (name == NULL || strstr(name, "HTTP") == NULL) {
            fprintf(stderr, "FAIL: proto 7 is not HTTP\n");
            errors++;
        } else {
            passed++;
        }
    }

    /* 5. Well-known id 5 resolves to DNS. */
    {
        char *name = ndpi_get_proto_name(mod, NDPI_PROTOCOL_DNS);
        printf("OK: proto 5 name = %s\n", name ? name : "(null)");
        if (name == NULL || strstr(name, "DNS") == NULL) {
            fprintf(stderr, "FAIL: proto 5 is not DNS\n");
            errors++;
        } else {
            passed++;
        }
    }

    /* 6. Flow tracking structs have a sane size. */
    {
        unsigned int sz = ndpi_detection_get_sizeof_ndpi_flow_struct();
        printf("OK: flow struct size = %u\n", sz);
        if (sz == 0) {
            fprintf(stderr, "FAIL: flow struct size is 0\n");
            errors++;
        } else {
            passed++;
        }
    }

    /* 7. The library reports a non-empty revision string. */
    {
        const char *rev = ndpi_revision();
        printf("OK: revision = %s\n", rev ? rev : "(null)");
        if (rev == NULL || strlen(rev) == 0) {
            fprintf(stderr, "FAIL: empty revision\n");
            errors++;
        } else {
            passed++;
        }
    }

    ndpi_exit_detection_module(mod);

summary:
    if (errors > 0) {
        fprintf(stderr, "FAILED: %d error(s), %d passed\n", errors, passed);
        return 1;
    }
    printf("All %d ndpi consumer checks passed\n", passed);
    return 0;
}
