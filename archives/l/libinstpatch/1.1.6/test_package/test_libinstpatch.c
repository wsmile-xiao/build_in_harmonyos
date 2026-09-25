#include <stdio.h>
#include <string.h>
#include <libinstpatch/libinstpatch.h>

int main(void)
{
    /* 1. library initialisation entry point callable */
    ipatch_init();

    /* 2. version string exported */
    const char *ver = IPATCH_VERSION;
    if (ver == NULL || ver[0] == '\0') {
        printf("FAIL: empty IPATCH_VERSION\n");
        return 1;
    }
    printf("PASS: IPATCH_VERSION = %s\n", ver);

    /* 3. sample transform object create/alloc/destroy (gobject pipeline,
     *    same call shape as upstream tests/sample_test.c) */
    IpatchSampleTransform *trans = ipatch_sample_transform_new(0, 0, 0);
    if (trans == NULL) {
        printf("FAIL: ipatch_sample_transform_new returned NULL\n");
        return 1;
    }
    ipatch_sample_transform_alloc_size(trans, 32 * 1024);
    ipatch_sample_transform_free(trans);
    printf("PASS: ipatch_sample_transform_new + alloc_size + free\n");

    /* 4. SF2 generator static table query (pure lookup, no object state) */
    const char *prop_name = ipatch_sf2_gen_get_prop_name(IPATCH_SF2_GEN_SAMPLE_END);
    if (prop_name == NULL || prop_name[0] == '\0') {
        printf("FAIL: ipatch_sf2_gen_get_prop_name returned empty\n");
        return 1;
    }
    printf("PASS: ipatch_sf2_gen_get_prop_name(%d) = %s\n",
           IPATCH_SF2_GEN_SAMPLE_END, prop_name);

    /* 5. GError helper (pure formatting function) */
    GError *err = g_error_new(g_quark_from_static_string("test-quark"), 42,
                              "boom %d", 7);
    const char *msg = ipatch_gerror_message(err);
    if (msg == NULL || strstr(msg, "boom") == NULL) {
        printf("FAIL: ipatch_gerror_message gave %p\n", (const void *)msg);
        return 1;
    }
    printf("PASS: ipatch_gerror_message = %s\n", msg);
    g_error_free(err);

    printf("OK: libinstpatch API test passed\n");
    return 0;
}
