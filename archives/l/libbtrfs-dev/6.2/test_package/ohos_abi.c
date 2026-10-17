#include <btrfs/ctree.h>
#include <btrfs/ioctl.h>

#include <stddef.h>
#include <stdio.h>

#if !defined(__aarch64__)
#error "This HarmonyOS PC ABI check must run for the aarch64 target"
#endif

_Static_assert(sizeof(void *) == 8, "expected a 64-bit HarmonyOS PC ABI");
_Static_assert(sizeof(long) == 8, "expected the HarmonyOS PC LP64 ABI");
_Static_assert(sizeof(struct btrfs_ioctl_search_header) == 32,
               "unexpected btrfs search-header ABI size");
_Static_assert(sizeof(struct btrfs_ioctl_search_key) == 104,
               "unexpected btrfs search-key ABI size");
_Static_assert(offsetof(struct btrfs_ioctl_search_key, unused1) == 72,
               "unexpected btrfs search-key field alignment");

int main(void)
{
    puts("HarmonyOS PC AArch64 LP64 btrfs ioctl ABI is available");
    return 0;
}
