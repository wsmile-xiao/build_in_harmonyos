/* Consumer test: compile, link and call the real libspatialindex C API. */
#include <stdio.h>
#include <stdlib.h>

#include <spatialindex/capi/sidx_api.h>
#include <spatialindex/capi/sidx_config.h>

static int failures = 0;

#define CHECK(cond)                                                    \
    do {                                                               \
        if (!(cond)) {                                                 \
            fprintf(stderr, "FAIL: %s at line %d\n", #cond, __LINE__); \
            failures++;                                                \
        }                                                              \
    } while (0)

int main(void)
{
    IndexPropertyH props = IndexProperty_Create();
    CHECK(props != NULL);
    CHECK(IndexProperty_SetIndexType(props, RT_RTree) == RT_None);
    CHECK(IndexProperty_SetIndexStorage(props, RT_Memory) == RT_None);
    CHECK(IndexProperty_SetDimension(props, 2) == RT_None);

    IndexH idx = Index_Create(props);
    CHECK(idx != NULL);
    IndexProperty_Destroy(props);
    if (idx == NULL) {
        return 1;
    }

    double min1[2] = {0.0, 0.0};
    double max1[2] = {1.0, 1.0};
    double min2[2] = {0.5, 0.5};
    double max2[2] = {1.5, 1.5};
    double min3[2] = {10.0, 10.0};
    double max3[2] = {11.0, 11.0};
    CHECK(Index_InsertData(idx, 1, min1, max1, 2, NULL, 0) == RT_None);
    CHECK(Index_InsertData(idx, 2, min2, max2, 2, NULL, 0) == RT_None);
    CHECK(Index_InsertData(idx, 3, min3, max3, 2, NULL, 0) == RT_None);

    uint64_t nResults = 0;
    int64_t *items = NULL;
    double qmin[2] = {0.25, 0.25};
    double qmax[2] = {1.75, 1.75};
    CHECK(Index_Intersects_id(idx, qmin, qmax, 2, &items, &nResults) == RT_None);
    printf("intersects query returned %llu item(s)\n", (unsigned long long)nResults);
    CHECK(nResults == 2);
    if (items != NULL) {
        free(items);
    }

    Index_Destroy(idx);

    if (failures != 0) {
        fprintf(stderr, "test_consumer: %d check(s) failed\n", failures);
        return 1;
    }
    printf("test_consumer PASSED\n");
    return 0;
}
