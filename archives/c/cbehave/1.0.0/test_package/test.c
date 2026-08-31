/*
 * test.c — test_package consumer test for cbehave.
 *
 * Exercise the public cbehave API (FEATURE/SCENARIO macros, assertion
 * macros and cbehave_runner) from a consumer's point of view:
 * the package must export cbehave.h / apr_ring.h and a linkable
 * libcbehave.
 */

#include <string.h>
#include "cbehave.h"

FEATURE(1, "Assertion macros provided by cbehave")
    SCENARIO("SHOULD_INT_EQUAL compares integers")

        GIVEN("two equal integers")
            int a = 42;
            int b = 42;
        GIVEN_END

        WHEN("we compare them")

        WHEN_END

        THEN("they match")
            SHOULD_INT_EQUAL(a, b);
        THEN_END

    SCENARIO_END

    SCENARIO("SHOULD_STR_EQUAL compares strings")

        GIVEN("equal strings")

            const char *s1 = "cbehave";
            const char *s2 = "cbehave";
        GIVEN_END

        WHEN("we compare them")
            /* nothing to do, assertions below */
        WHEN_END

        THEN("they match")
            SHOULD_STR_EQUAL(s1, s2);
        THEN_END

    SCENARIO_END

    SCENARIO("SHOULD_MEM_EQUAL compares buffers")

        GIVEN("equal memory buffers")
            const char buf1[4] = { 'a', 'b', 'c', 'd' };
            const char buf2[4] = { 'a', 'b', 'c', 'd' };
        GIVEN_END

        WHEN("we compare them")
            /* nothing to do, assertions below */
        WHEN_END

        THEN("they match")
            SHOULD_MEM_EQUAL(buf1, buf2, 4);
        THEN_END

    SCENARIO_END

    SCENARIO("SHOULD_BE_TRUE checks a condition")

        GIVEN("a true condition")
            int cond = (5 > 3);
        GIVEN_END

        WHEN("we evaluate it")
            /* nothing to do, assertions below */
        WHEN_END

        THEN("it is true")
            SHOULD_BE_TRUE(cond);
        THEN_END

    SCENARIO_END
FEATURE_END

int main(void) {
    cbehave_feature features[] = {
        {feature_idx(1)},
    };

    return cbehave_runner("cbehave consumer test:", features);
}