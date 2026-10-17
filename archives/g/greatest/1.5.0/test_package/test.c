#include <stdio.h>
#include "greatest.h"

/* Simple test using greatest assertions */
TEST basic_assertion_test(void) {
    int x = 5;
    ASSERT_EQ(5, x);
    ASSERT(x > 0);
    PASS();
}

TEST string_assertion_test(void) {
    const char *msg = "greatest";
    ASSERT_STR_EQ("greatest", msg);
    PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char **argv) {
    GREATEST_MAIN_BEGIN();
    RUN_TEST(basic_assertion_test);
    RUN_TEST(string_assertion_test);
    GREATEST_MAIN_END();
}
