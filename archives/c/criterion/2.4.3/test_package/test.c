#include <stdlib.h>
#include <criterion/criterion.h>

Test(basic, smoke_test) {
    cr_assert(1 + 1 == 2, "Basic arithmetic check");
}

Test(basic, string_test) {
    const char *str = "hello criterion";
    cr_assert_str_eq(str, "hello criterion", "String comparison check");
}

Test(basic, memory_test) {
    void *ptr = malloc(100);
    cr_assert_not_null(ptr, "Memory allocation check");
    free(ptr);
}
