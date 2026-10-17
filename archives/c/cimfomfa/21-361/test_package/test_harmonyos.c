/* HarmonyOS-specific installed-package test for cimfomfa 21-361.
 *
 * This executable is compiled and run by the OHOS Conan profile. It rejects
 * a wrong target at compile time, obtains real page-size and UID values from
 * OHOS libc, and uses those values with the packaged libtingea APIs.
 */
#include <tingea/array.h>
#include <tingea/ting.h>

#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef __OHOS__
#error "HarmonyOS-specific test requires the OHOS compiler target"
#endif

#if !defined(__aarch64__) && !defined(_M_ARM64)
#error "HarmonyOS PC test requires the aarch64 target"
#endif

static int compare_long(const void *lhs, const void *rhs)
{
    const long left = *(const long *)lhs;
    const long right = *(const long *)rhs;
    return (left > right) - (left < right);
}

#define CHECK(condition)                                                       \
    do {                                                                       \
        if (!(condition)) {                                                    \
            fprintf(stderr, "HarmonyOS check failed at line %d: %s\n",      \
                    __LINE__, #condition);                                     \
            return 1;                                                          \
        }                                                                      \
    } while (0)

int main(void)
{
    const long page_size = sysconf(_SC_PAGESIZE);
    const uid_t uid = getuid();
    long page_sizes[3];
    long key;
    long *floor_value;
    long *ceil_value;
    mcxTing *platform;

    CHECK(page_size >= 4096);
    CHECK(page_size % (long)sizeof(void *) == 0);
    CHECK(uid != (uid_t)-1);
    CHECK(sizeof(void *) == 8);

    platform = mcxTingNew("HarmonyOS");
    CHECK(platform != NULL);
    CHECK(mcxTingAppend(platform, "/aarch64") == platform);
    CHECK(strcmp(platform->str, "HarmonyOS/aarch64") == 0);

    page_sizes[0] = page_size / 2;
    page_sizes[1] = page_size;
    page_sizes[2] = page_size * 2;
    key = page_size;
    floor_value = mcxBsearchFloor(&key, page_sizes, 3, sizeof(page_sizes[0]),
                                  compare_long);
    ceil_value = mcxBsearchCeil(&key, page_sizes, 3, sizeof(page_sizes[0]),
                                compare_long);
    CHECK(floor_value == &page_sizes[1]);
    CHECK(ceil_value == &page_sizes[1]);

    mcxTingFree(&platform);
    CHECK(platform == NULL);
    printf("cimfomfa HarmonyOS checks passed: page_size=%ld uid=%u\n",
           page_size, (unsigned int)uid);
    return 0;
}
