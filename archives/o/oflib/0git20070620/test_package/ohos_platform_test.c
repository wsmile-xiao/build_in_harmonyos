#include <ofapi/of_api.h>

#include <stdio.h>
#include <string.h>
#include <sys/utsname.h>

#define CHECK(condition, message)                                               \
    do {                                                                        \
        if (!(condition)) {                                                     \
            fprintf(stderr, "FAIL: %s (line %d)\n", (message), __LINE__);       \
            return 1;                                                           \
        }                                                                       \
    } while (0)

int main(void)
{
    struct utsname system_info;
    uint8_t bytes[] = {0x00, 0x00, 0x00, 0x2a};
    uint32_t value = 0;

    CHECK(uname(&system_info) == 0, "uname must succeed on HarmonyOS PC");
    CHECK(strcmp(system_info.sysname, "HarmonyOS") == 0,
          "the test must run on HarmonyOS");
    CHECK(strcmp(system_info.machine, "aarch64") == 0,
          "HarmonyOS PC must report AArch64");
    CHECK(sizeof(void *) == 8, "HarmonyOS PC must use a 64-bit ABI");
    CHECK(of_property_to_uint32(&value, bytes, sizeof(bytes)) == 1 && value == 42,
          "the packaged oflib API must execute on HarmonyOS PC");
    puts("oflib HarmonyOS PC platform test passed (5 assertions)");
    return 0;
}
