/* Consumer test for GNU Radio VOLK 3.3.0 on HarmonyOS PC (R34/R53).
 *
 * Links the packaged libvolk and exercises the real public API:
 *   - volk_get_machine()  : runtime SIMD dispatch selection
 *   - volk_get_alignment(): platform alignment contract
 *   - volk_malloc()/volk_free(): aligned allocation required by VOLK kernels
 *   - volk_32f_s32f_multiply_32f(): a SIMD-dispatched kernel
 *   - VOLK_VERSION_* macros: exactly 3.3.0
 *
 * The .codesign section of the packaged library is verified separately from
 * the test_package conanfile.py (OHOS ELF loader requirement).
 */

#include <math.h>
#include <stdint.h>
#include <stdio.h>

#include <volk/volk.h>

static int failures = 0;

#define CHECK(cond, msg)                    \
    do {                                    \
        if (cond) {                         \
            printf("PASS: %s\n", msg);      \
        } else {                            \
            printf("FAIL: %s\n", msg);      \
            failures++;                     \
        }                                   \
    } while (0)

int main(void)
{
    const char* machine = volk_get_machine();
    printf("volk machine: %s\n", machine ? machine : "(null)");
    CHECK(machine != NULL, "volk_get_machine() reports the selected machine");

    size_t alignment = volk_get_alignment();
    printf("volk alignment: %zu\n", alignment);
    CHECK(alignment >= sizeof(void*), "volk_get_alignment() >= pointer size");
    CHECK((alignment & (alignment - 1)) == 0, "volk_get_alignment() is a power of two");

    enum { N = 1024 };
    const float scalar = 2.5f;
    float* input = (float*)volk_malloc(N * sizeof(float), alignment);
    float* output = (float*)volk_malloc(N * sizeof(float), alignment);
    CHECK(input != NULL && output != NULL, "volk_malloc() returns buffers");
    CHECK(input != NULL && output != NULL &&
              ((uintptr_t)input % alignment) == 0 &&
              ((uintptr_t)output % alignment) == 0,
          "volk_malloc() honours the requested alignment");

    if (input == NULL || output == NULL) {
        volk_free(input);
        volk_free(output);
        printf("ASSERTIONS: 7, FAILURES: %d\n", failures);
        return 1;
    }

    for (int i = 0; i < N; i++) {
        input[i] = (float)i;
        output[i] = 0.0f;
    }
    volk_32f_s32f_multiply_32f(output, input, scalar, (unsigned int)N);

    int mismatches = 0;
    for (int i = 0; i < N; i++) {
        if (fabsf(output[i] - input[i] * scalar) > 1e-4f) {
            mismatches++;
        }
    }
    CHECK(mismatches == 0, "volk_32f_s32f_multiply_32f() multiplies 1024 samples");

    volk_free(input);
    volk_free(output);

    CHECK(VOLK_VERSION_MAJOR == 3 && VOLK_VERSION_MINOR == 3 && VOLK_VERSION_MAINT == 0,
          "VOLK_VERSION macros are 3.3.0");

    printf("ASSERTIONS: 7, FAILURES: %d\n", failures);
    return failures == 0 ? 0 : 1;
}
