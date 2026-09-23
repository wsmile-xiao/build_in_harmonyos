/* test_librb.c — librb 2.0.0 consumer test (R34: real API calls).
 *
 * Six checks covering the headline features, each printing one "PASS:" line;
 * main prints the "RESULT: N passed" summary and returns non-zero on any
 * failure. Patterns (capacities, flag combos) mirror upstream tests.c.
 */
#include <stdio.h>
#include <string.h>

#include <rb.h>

static int check_heap_basic(void)
{
    /* rb_new(8, ...) holds 7 ints; write 4, read 4, verify values. */
    struct rb *rb = rb_new(8, sizeof(int), 0);
    int wr[4] = {10, 20, 30, 40};
    int rd[4] = {0};
    int ok;

    if (rb == NULL)
        return 1;
    ok = rb_write(rb, wr, 4) == 4
        && rb_count(rb) == 4
        && rb_read(rb, rd, 4) == 4
        && rd[0] == 10 && rd[1] == 20 && rd[2] == 30 && rd[3] == 40;
    rb_destroy(rb);
    return ok ? 0 : 1;
}

static int check_count_space(void)
{
    /* Exact numbers copied from upstream count_and_space. */
    struct rb *rb = rb_new(16, 1, 0);
    char d[4];
    int ok;

    if (rb == NULL)
        return 1;
    ok = rb_space(rb) == 15
        && rb_count(rb) == 0
        && rb_write(rb, "123", 3) == 3
        && rb_space(rb) == 12
        && rb_count(rb) == 3
        && rb_read(rb, d, 4) == 3;
    rb_destroy(rb);
    return ok ? 0 : 1;
}

static int check_stack_init(void)
{
    /* Stack-allocated ring buffer (upstream stack_init pattern). */
    struct rb rb2;
    int buf[8];
    int m;

    if (rb_init(&rb2, buf, 8, sizeof(int), 0) != 0)
        return 1;
    m = 111;
    if (rb_write(&rb2, &m, 1) != 1)
    {
        rb_cleanup(&rb2);
        return 1;
    }
    m = 222;
    if (rb_write(&rb2, &m, 1) != 1)
    {
        rb_cleanup(&rb2);
        return 1;
    }
    m = 0;
    if (rb_read(&rb2, &m, 1) != 1 || m != 111)
    {
        rb_cleanup(&rb2);
        return 1;
    }
    m = 0;
    if (rb_read(&rb2, &m, 1) != 1 || m != 222)
    {
        rb_cleanup(&rb2);
        return 1;
    }
    rb_cleanup(&rb2);
    return 0;
}

static int check_growable(void)
{
    /* Growable buffer absorbs writes past the initial count (upstream grow). */
    struct rb *rb = rb_new(4, 1, rb_growable);
    char rdbuf[8] = {0};
    int ok;

    if (rb == NULL)
        return 1;
    ok = rb_write(rb, "123", 3) == 3
        && rb_write(rb, "456", 3) == 3
        && rb_read(rb, rdbuf, 6) == 6
        && strcmp(rdbuf, "123456") == 0;
    rb_destroy(rb);
    return ok ? 0 : 1;
}

static int check_peek_discard(void)
{
    /* rb_peek leaves data in place; rb_discard drops it (upstream peeking). */
    struct rb *rb = rb_new(8, sizeof(int), 0);
    int w[4] = {1, 2, 3, 4};
    int v[4] = {0};
    int ok;

    if (rb == NULL)
        return 1;
    ok = rb_write(rb, w, 4) == 4
        && rb_recv(rb, v, 2, rb_peek) == 2
        && v[0] == 1 && v[1] == 2
        && rb_discard(rb, 1) == 1
        && rb_read(rb, v, 3) == 3
        && v[0] == 2 && v[1] == 3 && v[2] == 4;
    rb_destroy(rb);
    return ok ? 0 : 1;
}

static int check_dynamic(void)
{
    /* Dynamic frame stores one variable-size message (upstream dynamic_simple). */
    struct rb *rb = rb_new(16, 1, rb_dynamic);
    char rdbuf[32] = {0};
    int ok;

    if (rb == NULL)
        return 1;
    ok = rb_write(rb, "hello", 6) == 6
        && rb_peek_size(rb) == 6
        && rb_read(rb, rdbuf, 32) == 6
        && strcmp(rdbuf, "hello") == 0;
    rb_destroy(rb);
    return ok ? 0 : 1;
}

int main(void)
{
    int failed = 0;

    if (check_heap_basic() == 0)
        printf("PASS: heap_basic\n");
    else
    {
        printf("FAIL: heap_basic\n");
        failed++;
    }
    if (check_count_space() == 0)
        printf("PASS: count_space\n");
    else
    {
        printf("FAIL: count_space\n");
        failed++;
    }
    if (check_stack_init() == 0)
        printf("PASS: stack_init\n");
    else
    {
        printf("FAIL: stack_init\n");
        failed++;
    }
    if (check_growable() == 0)
        printf("PASS: growable\n");
    else
    {
        printf("FAIL: growable\n");
        failed++;
    }
    if (check_peek_discard() == 0)
        printf("PASS: peek_discard\n");
    else
    {
        printf("FAIL: peek_discard\n");
        failed++;
    }
    if (check_dynamic() == 0)
        printf("PASS: dynamic\n");
    else
    {
        printf("FAIL: dynamic\n");
        failed++;
    }

    printf("RESULT: %d passed, %d failed\n", 6 - failed, failed);
    return failed ? 1 : 0;
}
