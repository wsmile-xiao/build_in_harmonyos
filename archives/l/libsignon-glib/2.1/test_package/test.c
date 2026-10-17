#include <stdio.h>
#include <libsignon-glib/signon-glib.h>
#include <libsignon-glib/signon-identity.h>

int main(void) {
    /* Test signon_identity_new - creates a new SignonIdentity object */
    SignonIdentity *identity = signon_identity_new();
    if (SIGNON_IS_IDENTITY(identity)) {
        printf("libsignon-glib test: signon_identity_new() succeeded\n");
        g_object_unref(identity);
    } else {
        fprintf(stderr, "libsignon-glib test: signon_identity_new() failed\n");
        return 1;
    }

    /* Test SIGNON_TYPE_IDENTITY to verify the type system is registered */
    GType identity_type = SIGNON_TYPE_IDENTITY;
    if (identity_type != G_TYPE_INVALID) {
        printf("libsignon-glib test: SIGNON_TYPE_IDENTITY = %lu\n", identity_type);
    } else {
        fprintf(stderr, "libsignon-glib test: failed to get SIGNON_TYPE_IDENTITY\n");
        return 1;
    }

    /* Test signon_error_quark to verify error handling is linked */
    GQuark error_quark = signon_error_quark();
    if (error_quark != 0) {
        printf("libsignon-glib test: signon_error_quark() = %u\n", (unsigned int)error_quark);
    } else {
        fprintf(stderr, "libsignon-glib test: signon_error_quark() returned 0\n");
        return 1;
    }

    printf("libsignon-glib test: ALL OK\n");
    return 0;
}
