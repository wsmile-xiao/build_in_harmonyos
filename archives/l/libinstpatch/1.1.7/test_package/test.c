#include <stdio.h>
#include <string.h>
#include <glib.h>
#include <libinstpatch/libinstpatch.h>

int main(void) {
    guint major = 0, minor = 0, micro = 0;
    GType base_type;

    ipatch_version(&major, &minor, &micro);
    if (major != IPATCH_VERSION_MAJOR || minor != IPATCH_VERSION_MINOR
        || micro != IPATCH_VERSION_MICRO) {
        fprintf(stderr, "version mismatch: %u.%u.%u != %s\n",
                major, minor, micro, IPATCH_VERSION);
        return 1;
    }
    if (strcmp(IPATCH_VERSION, "1.1.7") != 0) {
        fprintf(stderr, "unexpected version string: %s\n", IPATCH_VERSION);
        return 1;
    }

    /* Verify the library's GObject type system registers Ipatch types. */
    base_type = ipatch_base_get_type();
    if (base_type == 0 || g_type_name(base_type) == NULL) {
        fprintf(stderr, "ipatch_base_get_type() did not register a type\n");
        return 1;
    }
    if (strcmp(g_type_name(base_type), "IpatchBase") != 0) {
        fprintf(stderr, "unexpected base type name: %s\n", g_type_name(base_type));
        return 1;
    }

    printf("libinstpatch %u.%u.%u: API version and type registration PASSED\n",
           major, minor, micro);
    return 0;
}
