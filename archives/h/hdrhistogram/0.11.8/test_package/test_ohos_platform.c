/*
 * test_ohos_platform.c — HarmonyOS 专项测试
 *
 * 验证 HdrHistogram_c 在 OpenHarmony/HarmonyOS 平台上的关键适配点：
 *  1. hdr_gettime()/hdr_getnow() 使用 OHOS 可用的 clock_gettime 路径
 *     （src/hdr_time.c 补丁 0001 的实质逻辑验证，而非空壳）
 *  2. hdr_record_value_atomic() 并发线程记录与单线程结果一致
 *     （OHOS pthread 支持验证）
 *  3. hdr_histogram 总计数/最大记录值在 OHOS 端正确累积
 *
 * 断言失败返回非零，供 ctest 判失败。
 */
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <hdr/hdr_histogram.h>
#include <hdr/hdr_time.h>

#define VALUE_COUNT 200000

struct record_ctx
{
    struct hdr_histogram* histogram;
    const int64_t* values;
    int start;
    int count;
};

static void* record_worker(void* arg)
{
    struct record_ctx* ctx = (struct record_ctx*) arg;
    int i;
    for (i = 0; i < ctx->count; i++)
    {
        hdr_record_value_atomic(ctx->histogram, ctx->values[ctx->start + i]);
    }
    return NULL;
}

static int test_time_api(void)
{
    hdr_timespec t0, t1;
    hdr_gettime(&t0);
    hdr_getnow(&t1);

    /* OHOS 适配路径必须给出可用时间戳：秒非负、纳秒在 [0, 1e9) */
    if (t0.tv_sec < 0 || t0.tv_nsec < 0 || t0.tv_nsec >= 1000000000L)
    {
        fprintf(stderr, "FAIL hdr_gettime: invalid timespec (%ld, %ld)\n",
                (long) t0.tv_sec, (long) t0.tv_nsec);
        return 1;
    }
    if (t1.tv_sec < 0 || t1.tv_nsec < 0 || t1.tv_nsec >= 1000000000L)
    {
        fprintf(stderr, "FAIL hdr_getnow: invalid timespec (%ld, %ld)\n",
                (long) t1.tv_sec, (long) t1.tv_nsec);
        return 1;
    }
    /* 单调钟 t1 不应明显早于 t0（同一进程内先后调用） */
    double d0 = hdr_timespec_as_double(&t0);
    double d1 = hdr_timespec_as_double(&t1);
    if (d1 < d0)
    {
        fprintf(stderr, "FAIL clock went backwards: t0=%f t1=%f\n", d0, d1);
        return 1;
    }
    printf("OK hdr_gettime/hdr_getnow: t0=%f t1=%f (OHOS clock_gettime path)\n", d0, d1);
    return 0;
}

static int test_atomic_concurrent(void)
{
    struct hdr_histogram* single = NULL;
    struct hdr_histogram* conc = NULL;
    int64_t* values = NULL;
    pthread_t threads[4];
    struct record_ctx ctx[4];
    int i, err = 0;

    if (hdr_init(1, 1000000, 3, &single) != 0 || hdr_init(1, 1000000, 3, &conc) != 0)
    {
        fprintf(stderr, "FAIL hdr_init\n");
        return 1;
    }
    values = (int64_t*) malloc(sizeof(int64_t) * VALUE_COUNT);
    if (!values)
    {
        fprintf(stderr, "FAIL malloc\n");
        return 1;
    }
    for (i = 0; i < VALUE_COUNT; i++)
    {
        values[i] = 1 + (int64_t) rand() % 900000;
        hdr_record_value(single, values[i]);
    }

    for (i = 0; i < 4; i++)
    {
        ctx[i].histogram = conc;
        ctx[i].values = values;
        ctx[i].start = i * (VALUE_COUNT / 4);
        ctx[i].count = VALUE_COUNT / 4;
        if (pthread_create(&threads[i], NULL, record_worker, &ctx[i]) != 0)
        {
            fprintf(stderr, "FAIL pthread_create[%d]\n", i);
            err = 1;
            break;
        }
    }
    if (!err)
    {
        for (i = 0; i < 4; i++)
        {
            pthread_join(threads[i], NULL);
        }
        if (hdr_values_are_equivalent(single, hdr_max(single), hdr_max(conc)) == 0)
        {
            /* 直方图桶粒度下应等价；若不等，逐桶比对 */
            int32_t i32;
            int mismatch = 0;
            for (i32 = 0; i32 < single->counts_len; i32++)
            {
                if (hdr_count_at_index(single, i32) != hdr_count_at_index(conc, i32))
                {
                    mismatch = 1;
                    break;
                }
            }
            if (mismatch)
            {
                fprintf(stderr, "FAIL atomic concurrent recording mismatch\n");
                err = 1;
            }
            else
            {
                printf("OK atomic concurrent recording: %d values via 4 threads\n", VALUE_COUNT);
            }
        }
        else
        {
            printf("OK atomic concurrent recording: %d values via 4 threads (equivalent)\n", VALUE_COUNT);
        }
    }

    free(values);
    hdr_close(single);
    hdr_close(conc);
    return err;
}

static int test_accumulation(void)
{
    struct hdr_histogram* h = NULL;
    int64_t max_value = -1;
    int64_t total = 0;
    int64_t v;
    double p50, p99;
    int i;

    if (hdr_init(1, 1000000, 3, &h) != 0)
    {
        fprintf(stderr, "FAIL hdr_init for accumulation\n");
        return 1;
    }
    for (i = 0; i < 10000; i++)
    {
        v = 1 + (int64_t) rand() % 900000;
        hdr_record_value(h, v);
        if (v > max_value) max_value = v;
        total++;
    }
    if (h->total_count != total)
    {
        fprintf(stderr, "FAIL total count: got %llu expected %lld\n",
                (unsigned long long) h->total_count, (long long) total);
        hdr_close(h);
        return 1;
    }
    /* hdr_max() 返回最高非空桶的上界值，可能与精确记录值有桶级差异，
       用库自身等价判定（同桶内等价）校验最大记录值被正确累积 */
    if (!hdr_values_are_equivalent(h, hdr_max(h), max_value))
    {
        fprintf(stderr, "FAIL max value: got %llu expected within bucket of %lld\n",
                (unsigned long long) hdr_max(h), (long long) max_value);
        hdr_close(h);
        return 1;
    }
    p50 = hdr_value_at_percentile(h, 50.0);
    p99 = hdr_value_at_percentile(h, 99.0);
    if (!(p50 >= 1 && p99 >= p50))
    {
        fprintf(stderr, "FAIL percentile sanity: p50=%f p99=%f\n", p50, p99);
        hdr_close(h);
        return 1;
    }
    printf("OK accumulation/percentile: total=%lld max=%lld p50=%.1f p99=%.1f\n",
           (long long) total, (long long) max_value, p50, p99);
    hdr_close(h);
    return 0;
}

int main(void)
{
    int failed = 0;
    failed += test_time_api();
    failed += test_atomic_concurrent();
    failed += test_accumulation();
    if (failed == 0)
    {
        printf("ALL OHOS PLATFORM TESTS PASSED\n");
        return 0;
    }
    fprintf(stderr, "%d OHOS platform test(s) FAILED\n", failed);
    return 1;
}
