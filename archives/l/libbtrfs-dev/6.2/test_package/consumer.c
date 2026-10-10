#include <btrfs/ctree.h>
#include <btrfs/ioctl.h>
#include <btrfs/send-stream.h>
#include <btrfs/sizes.h>

#include <stdio.h>

int main(void)
{
    struct btrfs_ioctl_search_key key = {0};
    int (*stream_api)(int, struct btrfs_send_ops *, void *, int, u64) =
        btrfs_read_and_process_send_stream;

    if (BTRFS_MAGIC == 0 || BTRFS_UUID_SIZE != 16 ||
        BTRFS_MAX_LEVEL == 0 || sizeof(key) == 0 || stream_api == NULL) {
        fputs("libbtrfs public header/link contract failed\n", stderr);
        return 1;
    }
    puts("libbtrfs headers, ABI and library symbol are available");
    return 0;
}
