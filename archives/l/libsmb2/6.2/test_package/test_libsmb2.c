/* test_package/test_libsmb2.c — libsmb2 6.2 consumer test (R34)
 * Calls real libsmb2 API: smb2_init_context, smb2_set_user,
 * smb2_parse_url, smb2_destroy_context
 *
 * Include order: smb2.h must be included before libsmb2.h
 * (struct smb2_timeval is defined in smb2.h, referenced by libsmb2.h)
 */
#include <stdio.h>
#include <string.h>
#include <time.h>

/* Include smb2.h first — it defines struct smb2_timeval, SMB2_GUID_SIZE */
#include <smb2/smb2.h>
/* Then libsmb2.h — it depends on smb2.h types */
#include <smb2/libsmb2.h>

int main(void) {
    /* Verify library is linked and version is accessible */
    struct smb2_libversion ver;
    memset(&ver, 0, sizeof(ver));
    smb2_get_libsmb2Version(&ver);
    if (ver.major_version == 0 && ver.minor_version == 0 && ver.patch_version == 0) {
        fprintf(stderr, "FAIL: smb2_get_libsmb2Version returned empty\n");
        return 1;
    }
    printf("libsmb2 version: %d.%d.%d\n",
           ver.major_version, ver.minor_version, ver.patch_version);

    /* Test context creation (core API) */
    struct smb2_context *smb2 = smb2_init_context();
    if (smb2 == NULL) {
        fprintf(stderr, "FAIL: smb2_init_context() returned NULL\n");
        return 1;
    }

    /* Test setting user (core API) */
    smb2_set_user(smb2, "testuser");

    /* Test URL parsing */
    struct smb2_url *url = smb2_parse_url(smb2, "smb://localhost/share");
    if (url == NULL) {
        fprintf(stderr, "FAIL: smb2_parse_url() returned NULL\n");
        smb2_destroy_context(smb2);
        return 1;
    }

    printf("smb2_parse_url: host=%s, share=%s\n",
           url->server ? url->server : "(null)",
           url->share ? url->share : "(null)");

    /* Clean up */
    smb2_destroy_url(url);
    smb2_destroy_context(smb2);

    printf("smb2_init_context + smb2_set_user + smb2_parse_url + destroy: OK\n");
    return 0;
}
