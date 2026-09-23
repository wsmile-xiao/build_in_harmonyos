#ifndef __OHOS__
#error "This test requires the HarmonyOS SDK"
#endif
#include <crunch64.h>
#include <deviceinfo.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#define REQUIRE(x) do { if (!(x)) { fprintf(stderr, "FAIL HarmonyOS line %d: %s\n", __LINE__, #x); goto cleanup; } } while (0)

int main(void)
{
    int result = 1, fd = -1;
    uint8_t *mapping = MAP_FAILED, *packed = NULL;
    size_t size = 0;
    char path[4096] = {0};
    const char *tmp = getenv("TMPDIR");
    const char *os = OH_GetOSFullName();
    int api = OH_GetSdkApiVersion();
    REQUIRE(tmp && *tmp && os && *os && api >= 10);
    long page = sysconf(_SC_PAGESIZE);
    REQUIRE(page > 0);
    size = (size_t)page * 2;
    REQUIRE(snprintf(path, sizeof(path), "%s/crunch64-ohos-XXXXXX", tmp) < (int)sizeof(path));
    fd = mkstemp(path);
    REQUIRE(fd >= 0);
    REQUIRE(ftruncate(fd, (off_t)size) == 0);
    mapping = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    REQUIRE(mapping != MAP_FAILED);
    /* Roundtrip actual OHOS device-info data across the Rust/C boundary and
       the user-writable HarmonyOS file mapping, including a page boundary. */
    size_t os_len = strlen(os);
    for (size_t i = 0; i < size; ++i) mapping[i] = (uint8_t)(os[i % os_len] ^ (uint8_t)api);
    size_t bound = 0;
    REQUIRE(crunch64_yaz0_compress_bound(&bound, size, mapping) == Crunch64Error_Okay);
    packed = malloc(bound);
    REQUIRE(packed != NULL);
    size_t packed_size = bound;
    REQUIRE(crunch64_yaz0_compress(&packed_size, packed, size, mapping) == Crunch64Error_Okay);
    memset(mapping, 0, size);
    size_t restored = size;
    REQUIRE(crunch64_yaz0_decompress(&restored, mapping, packed_size, packed) == Crunch64Error_Okay);
    REQUIRE(restored == size);
    REQUIRE(msync(mapping, size, MS_SYNC) == 0);
    REQUIRE(munmap(mapping, size) == 0);
    mapping = MAP_FAILED;
    mapping = mmap(NULL, size, PROT_READ, MAP_SHARED, fd, 0);
    REQUIRE(mapping != MAP_FAILED);
    for (size_t i = 0; i < size; ++i) REQUIRE(mapping[i] == (uint8_t)(os[i % os_len] ^ (uint8_t)api));
    printf("PASS HarmonyOS device-info + mmap roundtrip: os=%s api=%d bytes=%zu\n", os, api, size);
    result = 0;
cleanup:
    free(packed);
    if (mapping != MAP_FAILED && munmap(mapping, size) != 0) result = 1;
    if (fd >= 0) {
        if (close(fd) != 0) result = 1;
        if (unlink(path) != 0) result = 1;
    }
    return result;
}
