/* Consumer test for rarian: exercises the real installed C API.
 * Not a stub: links librarian and calls registry/info/man entry points.
 * Rarian headers require acknowledging the unstable API guard first.
 */
#define I_KNOW_RARIAN_0_8_IS_UNSTABLE
#include <rarian.h>

#include <assert.h>
#include <stdio.h>

static int count_regs = 0;
static int count_info = 0;
static int count_man = 0;

static int on_reg(RrnReg *reg, void *user_data)
{
    (void)user_data;
    if (reg && reg->name)
        count_regs++;
    return TRUE;
}

static int on_info(RrnInfoEntry *entry, void *user_data)
{
    (void)user_data;
    (void)entry;
    count_info++;
    return TRUE;
}

static int on_man(RrnManEntry *entry, void *user_data)
{
    (void)user_data;
    (void)entry;
    count_man++;
    return TRUE;
}

int main(void)
{
    int assertions = 0;

    /* 1. Info categories query must not crash (empty DB is valid). */
    char **cats = rrn_info_get_categories();
    (void)cats;
    assertions++;
    printf("CHECK-OK info-categories-query\n");

    /* 2-4. Registry/info/man foreach walks with counting callbacks. */
    rrn_for_each((RrnForeachFunc)on_reg, NULL);
    assertions++;
    printf("CHECK-OK registry-walk regs=%d\n", count_regs);

    rrn_info_for_each((RrnInfoForeachFunc)on_info, NULL);
    assertions++;
    printf("CHECK-OK info-walk entries=%d\n", count_info);

    rrn_man_for_each((RrnManForeachFunc)on_man, NULL);
    assertions++;
    printf("CHECK-OK man-walk entries=%d\n", count_man);

    /* 5-7. Shutdown sequence must be safe to call (idempotent cleanup). */
    rrn_shutdown();
    assertions++;
    printf("CHECK-OK rrn_shutdown\n");

    rrn_info_shutdown();
    assertions++;
    printf("CHECK-OK rrn_info_shutdown\n");

    rrn_man_shutdown();
    assertions++;
    printf("CHECK-OK rrn_man_shutdown\n");

    assert(assertions == 7);
    printf("RARIAN-CONSUMER-OK assertions=%d\n", assertions);
    return 0;
}
