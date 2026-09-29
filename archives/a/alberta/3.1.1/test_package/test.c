/* test.c -- test_package for alberta 3.1.1 (R34: real API calls).
 *
 * Exercises three public APIs of libalberta_utilities via the installed
 * <alberta_util.h> header:
 *   1. generate_filename() -- deterministic mesh/file name builder.
 *   2. MEM_ALLOC() / MEM_FREE() -- library memory allocator macros.
 *   3. add_parameter() / get_parameter() -- parameter database round-trip.
 */
#include <stdio.h>
#include <string.h>

#include <alberta_util.h>

static int check_filename(void)
{
    const char *name = generate_filename("/tmp", "mesh", 5);
    if (name == NULL || strcmp(name, "/tmp/mesh000005") != 0) {
        printf("FAIL filename: got '%s', want '/tmp/mesh000005'\n",
               name ? name : "(null)");
        return 1;
    }
    printf("PASS filename: %s\n", name);
    return 0;
}

static int check_mem_alloc(void)
{
    int i;
    double sum = 0.0;
    double *v = MEM_ALLOC(4, double);
    if (v == NULL) {
        printf("FAIL mem_alloc: allocator returned NULL\n");
        return 1;
    }
    for (i = 0; i < 4; i++)
        v[i] = (double)(i + 1);
    for (i = 0; i < 4; i++)
        sum += v[i];
    MEM_FREE(v, 4, double);
    if (sum != 10.0) {
        printf("FAIL mem_alloc: sum %f, want 10.0\n", sum);
        return 1;
    }
    printf("PASS mem_alloc: sum %f\n", sum);
    return 0;
}

static int check_parameter(void)
{
    int val = 0;
    int count;
    add_parameter(0, "alberta-test-key", "42");
    count = get_parameter(0, "alberta-test-key", "%d", &val);
    if (count != 1 || val != 42) {
        printf("FAIL parameter: count %d val %d, want 1 / 42\n", count, val);
        return 1;
    }
    printf("PASS parameter: val %d\n", val);
    return 0;
}

int main(void)
{
    int fails = 0;
    fails += check_filename();
    fails += check_mem_alloc();
    fails += check_parameter();
    if (fails == 0)
        printf("ALBERTA_TEST_ALL_PASS\n");
    return fails ? 1 : 0;
}
