/* test_package/test.c — libnfs consumer test (R34: substantive API use).
 *
 * Links against the packaged libnfs and exercises the public C API:
 *   - nfs_init_context()  : allocate a libnfs client context
 *   - nfs_parse_url_full(): parse an nfs:// URL into server/path/file
 *   - nfs_get_error()     : error text on failure
 *   - nfs_destroy_url()   : release the parsed URL
 *   - nfs_destroy_context(): release the context
 *
 * Note: <sys/time.h> must be included before <nfsc/libnfs.h> because the
 * latter embeds `struct timeval` in struct nfs_stat_64 without pulling in
 * the defining header itself.
 */
#include <sys/time.h>
#include <stdio.h>
#include <string.h>

#include <nfsc/libnfs.h>

int main(void)
{
    struct nfs_context *nfs = nfs_init_context();
    if (nfs == NULL) {
        printf("FAIL: nfs_init_context() returned NULL\n");
        return 1;
    }
    printf("PASS: nfs_init_context()\n");

    struct nfs_url *url = nfs_parse_url_full(nfs, "nfs://127.0.0.1/export/dir/file.txt");
    if (url == NULL) {
        printf("FAIL: nfs_parse_url_full(): %s\n", nfs_get_error(nfs));
        nfs_destroy_context(nfs);
        return 1;
    }
    printf("PASS: nfs_parse_url_full() server=%s path=%s file=%s\n",
           url->server ? url->server : "(null)",
           url->path ? url->path : "(null)",
           url->file ? url->file : "(null)");

    if (url->server == NULL || strcmp(url->server, "127.0.0.1") != 0) {
        printf("FAIL: unexpected server field\n");
        nfs_destroy_url(url);
        nfs_destroy_context(nfs);
        return 1;
    }
    if (url->path == NULL || strcmp(url->path, "/export/dir") != 0) {
        printf("FAIL: unexpected path field\n");
        nfs_destroy_url(url);
        nfs_destroy_context(nfs);
        return 1;
    }
    if (url->file == NULL || strstr(url->file, "file.txt") == NULL) {
        printf("FAIL: unexpected file field\n");
        nfs_destroy_url(url);
        nfs_destroy_context(nfs);
        return 1;
    }
    printf("PASS: url fields validated\n");

    nfs_destroy_url(url);
    nfs_destroy_context(nfs);
    printf("PASS: nfs_destroy_url() + nfs_destroy_context()\n");

    printf("test libnfs 5.0.3: OK\n");
    return 0;
}
