#include <CVector.h>

#include <stdio.h>
#include <string.h>

#define CHECK(condition, message) do { \
    if (!(condition)) { \
        fprintf(stderr, "FAIL: %s (line %d)\n", message, __LINE__); \
        failures++; \
    } else { \
        passes++; \
    } \
} while (0)

int main(void) {
    CVectorHandle vec = NULL;
    int failures = 0;
    int passes = 0;
    size_t i;
    double element;
    double buffer[16];

    /* Create: double elements, small initial capacity. */
    CHECK(CVectorCreate(&vec, sizeof(double), 4) == 0, "CVectorCreate succeeds");
    CHECK(vec != NULL, "handle is non-null");
    CHECK(CVectorSize(vec) == 0, "initial size is zero");

    /* Push 10 elements, forcing growth beyond initial capacity. */
    for (i = 0; i < 10; i++) {
        element = (double)(i * 2);
        CHECK(CVectorAddElement(vec, &element) == 0, "CVectorAddElement succeeds");
    }
    CHECK(CVectorSize(vec) == 10, "size is 10 after pushes");
    CHECK(CVectorCapacity(vec) >= 10, "capacity grew to hold 10 elements");

    /* Direct array read-back. */
    for (i = 0; i < 10; i++) {
        double got = ((double *)(vec->array))[i];
        CHECK(got == (double)(i * 2), "array read-back matches");
    }

    /* Copy-semantics read via CVectorGetElement. */
    for (i = 0; i < 10; i++) {
        element = -1.0;
        CHECK(CVectorGetElement(vec, &element, i) == 0, "CVectorGetElement succeeds");
        CHECK(element == (double)(i * 2), "CVectorGetElement value matches");
    }

    /* Pointer access via CVectorGetElementptr. */
    for (i = 0; i < 10; i++) {
        void *ptr = NULL;
        CHECK(CVectorGetElementptr(vec, &ptr, i) == 0, "CVectorGetElementptr succeeds");
        CHECK(ptr != NULL && *(double *)ptr == (double)(i * 2),
              "element pointer value matches");
        CHECK(CVectorElementAt(vec, i) == ptr, "CVectorElementAt agrees with pointer");
    }

    /* CVectorGetElementptr sets CVECTOR_FLAGS_NO_RELOCATION (see CVector.c);
       upstream CVectorBasicTest.c clears it via CVectorSetFlags(vec, 0) before
       Remove/Clear/Free. Mirror that so removal and free are permitted. */
    {
        unsigned int flags = 0;
        CHECK(CVectorGetFlags(vec, &flags) == 0, "CVectorGetFlags succeeds");
        CHECK((flags & CVECTOR_FLAGS_NO_RELOCATION) != 0,
              "NO_RELOCATION set by GetElementptr");
        CHECK(CVectorSetFlags(vec, 0) == 0, "CVectorSetFlags clears flags");
    }

    /* Overwrite via CVectorSetElement and verify. */
    for (i = 0; i < 10; i++) {
        element = (double)(100 + i);
        CHECK(CVectorSetElement(vec, &element, i) == 0, "CVectorSetElement succeeds");
    }
    for (i = 0; i < 10; i++) {
        element = 0.0;
        CVectorGetElement(vec, &element, i);
        CHECK(element == (double)(100 + i), "updated value matches");
    }

    /* Bulk read of the first 16 slots into a stack buffer via memcpy
       from the vector array (covers contiguous storage guarantee). */
    memcpy(buffer, vec->array, 10 * sizeof(double));
    CHECK(buffer[0] == 100.0 && buffer[9] == 109.0, "contiguous storage check");

    /* Remove one middle element: size shrinks, tail shifts down. */
    CHECK(CVectorRemoveElement(vec, 0) == 0, "CVectorRemoveElement succeeds");
    CHECK(CVectorSize(vec) == 9, "size is 9 after removal");
    element = 0.0;
    CVectorGetElement(vec, &element, 0);
    CHECK(element == 101.0, "elements shifted after removal");

    /* Clear resets size to zero. */
    CHECK(CVectorClear(vec) == 0, "CVectorClear succeeds");
    CHECK(CVectorSize(vec) == 0, "size is zero after clear");

    /* Reuse after clear, then free. */
    element = 42.0;
    CHECK(CVectorAddElement(vec, &element) == 0, "push after clear succeeds");
    CHECK(CVectorSize(vec) == 1, "size is 1 after re-push");
    CHECK(CVectorFree(&vec) == 0, "CVectorFree succeeds");
    CHECK(vec == NULL, "handle nulled after free");

    if (failures != 0) {
        fprintf(stderr, "cvector consumer test failed: %d failure(s), %d passed\n",
                failures, passes);
        return 1;
    }
    printf("cvector consumer test passed: %d assertions\n", passes);
    return 0;
}
