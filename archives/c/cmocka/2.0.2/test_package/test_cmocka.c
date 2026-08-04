#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <cmocka.h>

static void test_addition(void **state)
{
    (void)state;
    assert_int_equal(2 + 2, 4);
}

static void test_pointer_is_set(void **state)
{
    const char *value = "cmocka";

    (void)state;
    assert_non_null(value);
    assert_string_equal(value, "cmocka");
}

int main(void)
{
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_addition),
        cmocka_unit_test(test_pointer_is_set),
    };

    return cmocka_run_group_tests(tests, NULL, NULL);
}
