/* util-linux test_package consumer probe.
 * Uses libblkid (blkid_new_probe_from_filename) — verifies libblkid
 * links and initializes on OHOS.
 */
#include <blkid/blkid.h>
#include <stdio.h>

int main(void)
{
    blkid_probe pr = blkid_new_probe();
    if (pr == NULL) {
        fprintf(stderr, "FAIL: blkid_new_probe() returned NULL\n");
        return 1;
    }
    blkid_free_probe(pr);
    printf("util-linux OK\n");
    return 0;
}
