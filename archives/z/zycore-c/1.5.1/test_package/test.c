#include <stdio.h>

#include <Zycore/Vector.h>

int main(void)
{
    ZyanVector vector;
    const ZyanU32 values[] = { 7, 11, 13 };
    ZyanUSize size = 0;
    const ZyanU32 *stored = ZYAN_NULL;

    if (!ZYAN_SUCCESS(ZyanVectorInit(&vector, sizeof(values[0]), 1, ZYAN_NULL))) {
        return 1;
    }
    for (ZyanUSize index = 0; index < ZYAN_ARRAY_LENGTH(values); ++index) {
        if (!ZYAN_SUCCESS(ZyanVectorPushBack(&vector, &values[index]))) {
            ZyanVectorDestroy(&vector);
            return 2;
        }
    }
    if (!ZYAN_SUCCESS(ZyanVectorGetSize(&vector, &size)) || size != 3 ||
        !ZYAN_SUCCESS(ZyanVectorGetPointer(&vector, 1, (const void **)&stored)) ||
        *stored != 11) {
        ZyanVectorDestroy(&vector);
        return 3;
    }
    if (!ZYAN_SUCCESS(ZyanVectorDestroy(&vector))) {
        return 4;
    }

    puts("zycore-c vector consumer test passed");
    return 0;
}