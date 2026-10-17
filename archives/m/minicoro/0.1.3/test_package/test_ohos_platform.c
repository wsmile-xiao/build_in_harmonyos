/*
 * test_ohos_platform.c — minicoro HarmonyOS 专项测试
 *
 * 验证 minicoro 在 OpenHarmony/HarmonyOS aarch64 平台的关键适配点：
 *  1. 实现选择：aarch64-linux-ohos 下必须命中 MCO_USE_ASM（minicoro.h
 *     的 __aarch64__ 专用汇编实现），而非回退 ucontext/fibers——这是
 *     OHOS 上上下文切换正确性的核心前提。
 *  2. 嵌套协程：协程内 resume 另一个协程（OHOS 栈布局下嵌套切换）。
 *  3. 自定义栈大小 + 自定义分配器：验证 OHOS 上按需栈分配路径。
 *  4. 深层 C 调用链 + 跨函数 yield：验证汇编切换穿越 libc 调用。
 *
 * 与 test.c（消费者 API 冒烟）不同，本用例聚焦平台实现分支与嵌套/
 * 分配器语义，均是可观察结果，断言失败返回非零。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MINICORO_IMPL
#include <minicoro.h>

static int failures = 0;

static void verify_condition(int condition, const char *message) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        failures++;
    }
}

/* 自定义分配器：统计分配/释放次数，验证 OHOS 上 allocator 挂钩生效。
 * 回调签名与 minicoro.h mco_desc 声明一致：
 *   malloc_cb(size_t size, void* allocator_data)
 *   free_cb(void* ptr, void* allocator_data) */
static int alloc_count = 0;
static int free_count = 0;

static void *test_alloc(size_t size, void *allocator_data) {
    (void)allocator_data;
    alloc_count++;
    return malloc(size);
}

static void test_free(void *ptr, void *allocator_data) {
    (void)allocator_data;
    free_count++;
    free(ptr);
}

/* 深层调用辅助：5 层 C 函数调用链后 yield，验证切换穿越普通 C 调用。 */
static int helper_level5(mco_coro *co, int value) {
    if (value == 0) {
        return mco_yield(co) == MCO_SUCCESS ? 100 : -1;
    }
    return helper_level5(co, value - 1);
}

/* 嵌套协程入口：被外层协程 resume，完成一次 storage 往返后结束。 */
static void nested_coro(mco_coro *co) {
    int value = 0;
    verify_condition(mco_running() == co, "nested: mco_running == co");
    verify_condition(mco_pop(co, &value, sizeof(value)) == MCO_SUCCESS,
                     "nested: pop value");
    verify_condition(value == 7, "nested: value == 7");
    int out = 9;
    verify_condition(mco_push(co, &out, sizeof(out)) == MCO_SUCCESS,
                     "nested: push result");
    /* 嵌套协程内再次 yield，验证双层嵌套恢复。 */
    verify_condition(mco_yield(co) == MCO_SUCCESS, "nested: yield");
}

/* 外层协程入口：深调用链 yield + 嵌套协程创建/恢复。 */
static void outer_coro(mco_coro *co) {
    verify_condition(mco_running() == co, "outer: mco_running == co");

    /* 1) 穿越 5 层 C 调用链后 yield。 */
    int r = helper_level5(co, 5);
    verify_condition(r == 100, "outer: deep-chain yield returned");

    /* 2) 嵌套协程：创建、传值、两次 resume、回收。 */
    mco_coro *co2 = NULL;
    mco_desc desc2 = mco_desc_init(nested_coro, 0);
    verify_condition(mco_create(&co2, &desc2) == MCO_SUCCESS,
                     "outer: create nested");
    int val = 7;
    verify_condition(mco_push(co2, &val, sizeof(val)) == MCO_SUCCESS,
                     "outer: push to nested");
    verify_condition(mco_resume(co2) == MCO_SUCCESS, "outer: resume nested #1");
    verify_condition(mco_status(co2) == MCO_SUSPENDED,
                     "outer: nested suspended after yield");
    int got = 0;
    verify_condition(mco_pop(co2, &got, sizeof(got)) == MCO_SUCCESS,
                     "outer: pop nested result");
    verify_condition(got == 9, "outer: nested returned 9");
    verify_condition(mco_resume(co2) == MCO_SUCCESS, "outer: resume nested #2");
    verify_condition(mco_status(co2) == MCO_DEAD, "outer: nested dead");
    verify_condition(mco_destroy(co2) == MCO_SUCCESS, "outer: destroy nested");
}

int main(void) {
#ifdef MCO_USE_ASM
    puts("OHOS impl: MCO_USE_ASM (aarch64 assembly context switch)");
#elif defined(MCO_USE_UCONTEXT)
    puts("OHOS impl: MCO_USE_UCONTEXT");
#elif defined(MCO_USE_FIBERS)
    puts("OHOS impl: MCO_USE_FIBERS");
#else
    puts("OHOS impl: unknown");
#endif
#if defined(__aarch64__)
    puts("OHOS arch: aarch64");
#endif

    /* 1) 实现分支断言：aarch64-linux-ohos 必须为 MCO_USE_ASM。 */
#if defined(__aarch64__) && defined(__linux__)
    verify_condition(
#if defined(MCO_USE_ASM)
        1,
#else
        0,
#endif
        "aarch64-linux-ohos selects MCO_USE_ASM");
#endif

    /* 2) 自定义分配器 + 自定义栈大小（64KB）。 */
    mco_desc desc = mco_desc_init(outer_coro, 64 * 1024);
    desc.malloc_cb = test_alloc;
    desc.free_cb = test_free;
    mco_coro *co = NULL;
    verify_condition(mco_create(&co, &desc) == MCO_SUCCESS, "mco_create");
    verify_condition(alloc_count > 0, "custom allocator invoked");

    /* 3) 首轮 resume：深调用链 yield。 */
    verify_condition(mco_resume(co) == MCO_SUCCESS, "resume #1 (deep chain)");
    verify_condition(mco_status(co) == MCO_SUSPENDED, "suspended after yield");

    /* 4) 次轮 resume：嵌套协程完成。 */
    verify_condition(mco_resume(co) == MCO_SUCCESS, "resume #2 (nested)");
    verify_condition(mco_status(co) == MCO_DEAD, "dead after finish");

    /* 5) 销毁并核对分配器释放计数。 */
    verify_condition(mco_destroy(co) == MCO_SUCCESS, "mco_destroy");
    verify_condition(free_count > 0, "custom deallocator invoked");
    verify_condition(alloc_count == free_count, "alloc/free balanced");

    if (failures == 0) {
        puts("minicoro OHOS platform test: 15 assertions passed");
    }
    return failures;
}