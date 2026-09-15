/* test.c — test_package for fff 1.1 (R34 consumer test).
 *
 * fff is a header-only fake/mock framework, so the consumer test compiles
 * against the installed <fff.h> and asserts real framework behaviour from a
 * library-user's perspective:
 *   1. FAKE_VOID_FUNC: call_count starts at 0 and counts real calls
 *   2. argument capture: arg0_val + arg0_history entries
 *   3. global call history: fff.call_history records call order per fake
 *   4. FAKE_VALUE_FUNC: default return 0, then return_val_seq sequence and
 *      its "repeat last element after exhaustion" contract
 *   5. custom_fake takeover
 *   6. RESET_FAKE / FFF_RESET_HISTORY() reset semantics
 *
 * The test fails to compile/link when the package artifacts are removed,
 * satisfying the CI L1e destructive negative test. Exit code: 0 = all
 * assertions passed, 1 = at least one failure.
 */
#include <stdio.h>
#include <string.h>

#include <fff.h>

/* 单翻译单元消费者：必须 DEFINE_FFF_GLOBALS 才能引用 fff.call_history。 */
DEFINE_FFF_GLOBALS;

FAKE_VOID_FUNC(voidfunc1, int);
FAKE_VOID_FUNC(voidfunc2, char, char);
FAKE_VALUE_FUNC(long, longfunc0);

static int failures = 0;
static int total = 0;

static void check(int ok, const char *what)
{
    total++;
    if (ok) {
        printf("PASS: %s\n", what);
    } else {
        printf("FAIL: %s\n", what);
        failures++;
    }
}

/* longfunc0 为 FAKE_VALUE_FUNC(long, longfunc0)（0 参），custom_fake 签名
 * 必须是 long (*)(void)。 */
static long stub_meaning_of_life(void)
{
    return 42;
}

int main(void)
{
    /* 1. call_count 初始为 0（上游 when_void_func_never_called 语义） */
    check(voidfunc1_fake.call_count == 0u, "voidfunc1_fake.call_count starts at 0");

    /* 2. 调用计数与实参捕获 */
    voidfunc1(77);
    check(voidfunc1_fake.call_count == 1u, "voidfunc1(77) sets call_count to 1");
    check(voidfunc1_fake.arg0_val == 77, "arg0_val captures 77");
    check(voidfunc1_fake.arg0_history[0] == 77, "arg0_history[0] stores 77");

    voidfunc1(78);
    check(voidfunc1_fake.call_count == 2u, "second call sets call_count to 2");
    check(voidfunc1_fake.arg0_history[1] == 78, "arg0_history[1] stores 78");

    /* 3. 全局调用历史按 fake 函数指针记录调用顺序（上游口径：(void*)funcname） */
    voidfunc2('a', 'b');
    check(fff.call_history_idx == 3u, "fff.call_history_idx counts 3 fake calls");
    check(fff.call_history[0] == (fff_function_t)voidfunc1,
          "call_history[0] is voidfunc1");
    check(fff.call_history[1] == (fff_function_t)voidfunc1,
          "call_history[1] is voidfunc1");
    check(fff.call_history[2] == (fff_function_t)voidfunc2,
          "call_history[2] is voidfunc2");
    check(voidfunc2_fake.arg1_val == 'b', "voidfunc2 captures second char arg");

    /* 4. 值函数默认返回 0 */
    check(longfunc0() == 0, "value fake returns 0 by default");
    check(longfunc0_fake.call_count == 1u, "longfunc0_fake.call_count counts the call");

    /* 5. 返回值序列：依次返回，耗尽后重复最后一个元素 */
    {
        long seq[3] = {5, 6, 7};
        longfunc0_fake.return_val_seq = seq;
        longfunc0_fake.return_val_seq_len = 3;
        check(longfunc0() == 5, "return_val_seq returns 5 first");
        check(longfunc0() == 6, "return_val_seq returns 6 second");
        check(longfunc0() == 7, "return_val_seq returns 7 third");
        check(longfunc0() == 7, "exhausted sequence repeats last element");
    }

    /* 6. custom_fake 接管返回逻辑 */
    longfunc0_fake.custom_fake = stub_meaning_of_life;
    check(longfunc0() == 42, "custom_fake overrides the return value (42)");

    /* 7. RESET_FAKE 恢复默认行为（memset 零化） */
    RESET_FAKE(longfunc0);
    check(longfunc0_fake.call_count == 0u, "RESET_FAKE clears call_count");
    check(longfunc0_fake.return_val_seq == NULL, "RESET_FAKE clears return_val_seq");
    check(longfunc0() == 0, "value fake returns 0 again after reset");

    /* 8. FFF_RESET_HISTORY() 清全局调用历史 */
    FFF_RESET_HISTORY();
    check(fff.call_history_idx == 0u, "FFF_RESET_HISTORY clears call_history_idx");

    RESET_FAKE(voidfunc1);
    RESET_FAKE(voidfunc2);

    printf("\n-------------\n");
    if (failures == 0) {
        printf("fff consumer test: ALL %d assertions passed\n", total);
        printf("Complete\n");
        return 0;
    }
    printf("fff consumer test: %d of %d assertions FAILED\n", failures, total);
    return 1;
}
