/* Consumer-side checks for the xxhash/0.8.4 Conan package. */
#include <xxhash.h>

#include <inttypes.h>
#include <stdio.h>
#include <string.h>

static unsigned checks;
static unsigned failures;

#define CHECK(condition, description) do { \
    ++checks; \
    if (!(condition)) { \
        ++failures; \
        fprintf(stderr, "[FAIL] %s (%s:%d)\n", description, __FILE__, __LINE__); \
    } else { \
        printf("[ok] %s\n", description); \
    } \
} while (0)

int main(void)
{
    const char input[] = "HarmonyOS PC";
    const size_t input_size = sizeof(input) - 1;
    const XXH64_hash_t expected64 = XXH64(input, input_size, 17);
    const XXH64_hash_t changed64 = XXH64("HarmonYOS PC", input_size, 17);
    XXH64_state_t *state64 = XXH64_createState();
    XXH3_state_t *state3 = XXH3_createState();

    if (state64 == NULL || state3 == NULL) {
        fprintf(stderr, "Unable to allocate xxHash streaming state\n");
        if (state64 != NULL) XXH64_freeState(state64);
        if (state3 != NULL) XXH3_freeState(state3);
        return 2;
    }

    CHECK(XXH_versionNumber() == 804, "package reports xxHash 0.8.4");
    CHECK(XXH32("", 0, 0) == 0x02CC5D05U, "XXH32 empty-input reference vector");
    CHECK(XXH64("", 0, 0) == UINT64_C(0xEF46DB3751D8E999), "XXH64 empty-input reference vector");
    CHECK(XXH3_64bits("", 0) == UINT64_C(0x2D06800538D394C2), "XXH3-64 empty-input reference vector");
    CHECK(expected64 != changed64, "changing an input byte changes the XXH64 result");

    CHECK(XXH64_reset(state64, 17) == XXH_OK, "XXH64 streaming state resets");
    CHECK(XXH64_update(state64, input, 4) == XXH_OK, "XXH64 accepts the first input chunk");
    CHECK(XXH64_update(state64, input + 4, input_size - 4) == XXH_OK,
          "XXH64 accepts the remaining input chunk");
    CHECK(XXH64_digest(state64) == expected64, "XXH64 streaming result matches one-shot result");

    CHECK(XXH3_64bits_reset(state3) == XXH_OK, "XXH3-64 streaming state resets");
    CHECK(XXH3_64bits_update(state3, input, 4) == XXH_OK, "XXH3-64 accepts the first input chunk");
    CHECK(XXH3_64bits_update(state3, input + 4, input_size - 4) == XXH_OK,
          "XXH3-64 accepts the remaining input chunk");
    CHECK(XXH3_64bits_digest(state3) == XXH3_64bits(input, input_size),
          "XXH3-64 streaming result matches one-shot result");

    XXH64_freeState(state64);
    XXH3_freeState(state3);

    if (failures != 0) {
        fprintf(stderr, "\nxxHash consumer checks: %u/%u passed, %u failed\n", checks - failures, checks, failures);
        return 1;
    }
    printf("\nxxHash 0.8.4 consumer checks: %u/%u passed\n", checks, checks);
    return 0;
}
