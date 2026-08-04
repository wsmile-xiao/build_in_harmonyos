#include <stdio.h>
#include <string.h>

#include <librsync.h>

int main(void)
{
    rs_magic_number magic = 0;
    size_t block_len = 0;
    size_t strong_len = 0;
    rs_result result = rs_sig_args(4096, &magic, &block_len, &strong_len);

    if (result != RS_DONE) {
        fprintf(stderr, "rs_sig_args failed: %d\n", result);
        return 1;
    }
    if (magic == 0 || block_len == 0 || strong_len == 0) {
        fprintf(stderr, "rs_sig_args returned invalid values\n");
        return 1;
    }
    if (strstr(rs_librsync_version, "2.3.4") == NULL) {
        fprintf(stderr, "unexpected librsync version: %s\n", rs_librsync_version);
        return 1;
    }

    printf("librsync %s ok\n", rs_librsync_version);
    return 0;
}
