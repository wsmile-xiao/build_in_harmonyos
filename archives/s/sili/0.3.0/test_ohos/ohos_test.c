/*
 * OHOS 专项测试 — sili 0.3.0
 *
 * 通过公开 API 验证 sili 在 HarmonyOS PC (armv8, OHOS clang) 平台上的
 * 系统/线程/时间/字符串功能与可观察结果（与上游 tests 目录用例、test_package
 * 消费者用例分别计数）。
 *
 * 验证点：
 *   1. 线程创建/运行/join（si_threadMakeAndRun / si_threadJoin）
 *   2. 时间 API（si_timeNowUTC / si_timeNowLocal / si_sleep）
 *   3. 环境变量读写（si_envVarSet / si_envVarGetData / si_envVarUnset）
 *   4. 系统信息（si_cpuProcessorCount）
 *   5. 字符串 API（si_stringEqual / si_stringFromCStr / si_stringTrim）
 *
 * 任一断言失败即非零退出，全部通过返回 0。
 */
#define SI_IMPLEMENTATION 1
#include <sili.h>

#include <stdio.h>

static bool thread_ran = false;

static void* ohos_thread_entry(void* arg) {
    siString tag = *(siString*)arg;
    thread_ran = si_stringEqual(tag, SI_STR("ohos"));
    return thread_ran ? nil : (void*)1;
}

int main(void) {
    siAllocator alloc = si_allocatorHeap();

    /* 1. Thread: create, run, join with observable result. */
    siString tag = SI_STR("ohos");
    siThread thread = si_threadMake(ohos_thread_entry, &tag);
    siError err = si_threadRun(&thread);
    if (err.code != 0) {
        si_printfLn("FAIL: si_threadRun error %i", err.code);
        return 1;
    }
    err = si_threadJoin(&thread);
    if (err.code != 0 || !thread_ran) {
        si_printfLn("FAIL: si_threadJoin / thread_ran");
        return 1;
    }

    /* 2. Time: UTC and local timestamps must be non-zero and close. */
    siTime utc = si_timeNowUTC();
    siTime local = si_timeNowLocal();
    if (utc <= 0 || local <= 0) {
        si_printfLn("FAIL: si_timeNowUTC/Local non-positive");
        return 1;
    }
    si_sleep(SI_MILLISECOND * 5);

    /* 3. Environment variable round-trip. */
    siString name = SI_STR("SI_OHOS_TEST");
    siString value = SI_STR("harmonyos-pc");
    if (!si_envVarSet(name, value)) {
        si_printfLn("FAIL: si_envVarSet");
        return 1;
    }
    isize len = si_envVarGetLength(name);
    if (len != value.len) {
        si_printfLn("FAIL: si_envVarGetLength (%zi != %zi)", len, value.len);
        return 1;
    }
    siString out = si_envVarGetData(name, SI_ARR_STACK(1024));
    if (!si_stringEqual(out, value)) {
        si_printfLn("FAIL: si_envVarGetData content");
        return 1;
    }
    if (!si_envVarUnset(name)) {
        si_printfLn("FAIL: si_envVarUnset");
        return 1;
    }

    /* 4. System info: CPU count must be positive. */
    i32 cpus = si_cpuProcessorCount();
    if (cpus <= 0) {
        si_printfLn("FAIL: si_cpuProcessorCount (%i)", cpus);
        return 1;
    }

    /* 5. Strings: convert + trim. */
    siString conv = si_stringFromCStr("  harmony  ", alloc);
    siString trimmed = si_stringTrim(conv, SI_STR(" "));
    if (!si_stringEqual(trimmed, SI_STR("harmony"))) {
        si_printfLn("FAIL: si_stringFromCStr/si_stringTrim");
        return 1;
    }

    si_printfLn("ohos_test: all OHOS-specific checks passed (cpus=%i, utc=%li)",
                cpus, (long)utc);
    printf("sili OHOS test OK\n");
    return 0;
}
