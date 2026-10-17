#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <ratpoints.h>

static int point_count;
static int callback_state_ok = 1;

static int collect_point(long numerator, long denominator, const mpz_t y,
                         void *context, int *quit)
{
    (void)y;
    (void)context;
    if (denominator < 0 || numerator < -10 || numerator > 10) {
        callback_state_ok = 0;
    }
    ++point_count;
    *quit = 0;
    return 1;
}

static void require_condition(int condition, const char *description)
{
    if (!condition) {
        fprintf(stderr, "ratpoints assertion failed: %s\n", description);
        exit(EXIT_FAILURE);
    }
}

int main(void)
{
    mpz_t coefficients[3];
    ratpoints_interval domain[4];
    ratpoints_args args;
    long result;

    require_condition(RATPOINTS_MAX_DEGREE == 100, "maximum degree constant");
    require_condition(RATPOINTS_ARRAY_SIZE == 256, "array size constant");
    require_condition(RATPOINTS_DEFAULT_SP1 == 9, "first sieve default");
    require_condition(RATPOINTS_DEFAULT_SP2 == 16, "second sieve default");

    memset(&args, 0, sizeof(args));
    for (size_t index = 0; index < 3; ++index) {
        mpz_init(coefficients[index]);
    }
    mpz_set_si(coefficients[0], -1);
    mpz_set_si(coefficients[1], 0);
    mpz_set_si(coefficients[2], 1);
    require_condition(mpz_cmp_si(coefficients[2], 1) == 0, "GMP coefficient setup");

    args.cof = coefficients;
    args.degree = 2;
    args.height = 10;
    args.domain = domain;
    args.num_inter = 0;
    args.b_low = 1;
    args.b_high = 10;
    args.sp1 = RATPOINTS_DEFAULT_SP1;
    args.sp2 = RATPOINTS_DEFAULT_SP2;
    args.array_size = RATPOINTS_ARRAY_SIZE;
    args.sturm = RATPOINTS_DEFAULT_STURM;
    args.num_primes = RATPOINTS_DEFAULT_NUM_PRIMES;
    args.max_forbidden = RATPOINTS_DEFAULT_MAX_FORBIDDEN;
    args.flags = 0;

    result = find_points(&args, collect_point, NULL);
    require_condition(result == 12, "x^2 - 1 point count");
    require_condition(point_count == 12, "callback invocation count");
    require_condition(callback_state_ok, "callback point invariants");

    for (size_t index = 0; index < 3; ++index) {
        mpz_clear(coefficients[index]);
    }

#ifdef __OHOS__
    require_condition(sizeof(void *) == 8, "HarmonyOS PC pointer ABI is 64-bit");
    require_condition(sizeof(long) == 8, "HarmonyOS PC long ABI is 64-bit");
#endif

    puts("ratpoints public API test passed");
    return EXIT_SUCCESS;
}
