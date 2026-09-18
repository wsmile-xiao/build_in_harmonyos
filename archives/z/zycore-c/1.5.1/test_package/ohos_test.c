#include <stdio.h>

#include <Zycore/API/Thread.h>
#include <Zycore/String.h>
#include <Zycore/Vector.h>

/* HarmonyOS 专项测试：通过 zycore-c 公开 API 验证 OHOS 平台行为。
 *
 * 1. Thread TLS：ZyanThreadTls* 在 POSIX/OHOS 上由 pthread_key_* 支撑，
 *    直接验证配方对 OHOS 声明的 pthread 系统库链接与 TLS 运行时行为。
 * 2. ZyanString：上游字符串容器（内存分配走默认分配器）。
 * 3. ZyanVector：O(1) 索引访问与元素值校验。
 */

static int test_ohos_thread_tls(void)
{
    ZyanThreadTlsIndex index;
    if (!ZYAN_SUCCESS(ZyanThreadTlsAlloc(&index, ZYAN_NULL)))
    {
        return 1;
    }

    const int value = 0x2A2A2A2A;
    if (!ZYAN_SUCCESS(ZyanThreadTlsSetValue(index, (void*)(ZyanUSize)value)))
    {
        ZyanThreadTlsFree(index);
        return 2;
    }

    void* readback = ZYAN_NULL;
    if (!ZYAN_SUCCESS(ZyanThreadTlsGetValue(index, &readback)))
    {
        ZyanThreadTlsFree(index);
        return 3;
    }
    if ((ZyanUSize)readback != (ZyanUSize)value)
    {
        ZyanThreadTlsFree(index);
        return 4;
    }

    ZyanThreadId thread_id;
    if (!ZYAN_SUCCESS(ZyanThreadGetCurrentThreadId(&thread_id)) || (thread_id == 0))
    {
        ZyanThreadTlsFree(index);
        return 5;
    }

    ZyanThreadTlsFree(index);
    return 0;
}

static int test_ohos_string(void)
{
    ZyanString string;
    if (!ZYAN_SUCCESS(ZyanStringInit(&string, 8)))
    {
        return 1;
    }

    static const ZyanStringView view1 = ZYAN_DEFINE_STRING_VIEW("zycore-ohos");
    static const ZyanStringView view2 = ZYAN_DEFINE_STRING_VIEW("-1.5.1");
    if (!ZYAN_SUCCESS(ZyanStringAppend(&string, &view1)) ||
        !ZYAN_SUCCESS(ZyanStringAppend(&string, &view2)))
    {
        ZyanStringDestroy(&string);
        return 2;
    }

    /* "zycore-ohos-1.5.1" = 17 个字符（不含 NUL） */
    ZyanUSize length = 0;
    if (!ZYAN_SUCCESS(ZyanStringViewGetSize(ZYAN_STRING_TO_VIEW(&string), &length)) ||
        (length != 17))
    {
        ZyanStringDestroy(&string);
        return 3;
    }

    static const char expected[] = "zycore-ohos-1.5.1";
    for (ZyanUSize i = 0; i < length; ++i)
    {
        char value = 0;
        if (!ZYAN_SUCCESS(ZyanStringGetChar(ZYAN_STRING_TO_VIEW(&string), i, &value)) ||
            (value != expected[i]))
        {
            ZyanStringDestroy(&string);
            return 4;
        }
    }

    ZyanStringDestroy(&string);
    return 0;
}

static int test_ohos_vector(void)
{
    ZyanVector vector;
    if (!ZYAN_SUCCESS(ZyanVectorInit(&vector, sizeof(ZyanU32), 4, ZYAN_NULL)))
    {
        return 1;
    }

    const ZyanU32 expected[] = { 0x11111111, 0x22222222, 0x33333333, 0x44444444, 0x55555555 };
    for (ZyanUSize i = 0; i < ZYAN_ARRAY_LENGTH(expected); ++i)
    {
        if (!ZYAN_SUCCESS(ZyanVectorPushBack(&vector, &expected[i])))
        {
            ZyanVectorDestroy(&vector);
            return 2;
        }
    }

    ZyanUSize size = 0;
    if (!ZYAN_SUCCESS(ZyanVectorGetSize(&vector, &size)) ||
        (size != ZYAN_ARRAY_LENGTH(expected)))
    {
        ZyanVectorDestroy(&vector);
        return 3;
    }

    for (ZyanUSize i = 0; i < size; ++i)
    {
        const ZyanU32 value = ZYAN_VECTOR_GET(ZyanU32, &vector, i);
        if (value != expected[i])
        {
            ZyanVectorDestroy(&vector);
            return 4;
        }
    }

    ZyanVectorDestroy(&vector);
    return 0;
}

int main(void)
{
    int rc;

    rc = test_ohos_thread_tls();
    if (rc != 0)
    {
        printf("zycore-c ohos test failed at thread_tls step %d\n", rc);
        return rc;
    }

    rc = test_ohos_string();
    if (rc != 0)
    {
        printf("zycore-c ohos test failed at string step %d\n", rc);
        return rc;
    }

    rc = test_ohos_vector();
    if (rc != 0)
    {
        printf("zycore-c ohos test failed at vector step %d\n", rc);
        return rc;
    }

    puts("zycore-c ohos test passed");
    return 0;
}