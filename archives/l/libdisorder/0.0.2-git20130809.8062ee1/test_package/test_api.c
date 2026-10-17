#include <disorder.h>

#include <math.h>
#include <stdio.h>

static int checks = 0;

#define CHECK(condition)                                                        \
    do {                                                                        \
        ++checks;                                                               \
        if (!(condition)) {                                                     \
            fprintf(stderr, "check %d failed: %s\n", checks, #condition);     \
            return 1;                                                           \
        }                                                                       \
    } while (0)

static int close_to(float actual, float expected)
{
    return fabsf(actual - expected) < 0.00001f;
}

int main(void)
{
    char binary[] = {0, 1, 0, 1, 0, 1, 0, 1};
    char quaternary[] = {0, 1, 2, 3, 0, 1, 2, 3};
    char skewed[] = {'a', 'a', 'a', 'b'};
    char all_bytes[256];
    int i;

    CHECK(close_to(shannon_H(NULL, 0), 0.0f));

    CHECK(close_to(shannon_H(binary, sizeof(binary)), 1.0f));
    CHECK(get_num_tokens() == 2);
    CHECK(close_to(get_max_entropy(), 1.0f));
    CHECK(close_to(get_entropy_ratio(), 1.0f));

    CHECK(close_to(shannon_H(quaternary, sizeof(quaternary)), 2.0f));
    CHECK(get_num_tokens() == 4);
    CHECK(close_to(get_max_entropy(), 2.0f));
    CHECK(close_to(get_entropy_ratio(), 1.0f));

    for (i = 0; i < 256; ++i) {
        all_bytes[i] = (char)i;
    }
    CHECK(close_to(shannon_H(all_bytes, sizeof(all_bytes)), 8.0f));
    CHECK(get_num_tokens() == 256);
    CHECK(close_to(get_max_entropy(), 8.0f));
    CHECK(close_to(get_entropy_ratio(), 1.0f));

    CHECK(close_to(shannon_H(skewed, sizeof(skewed)), 0.811278f));
    CHECK(get_num_tokens() == 2);
    CHECK(close_to(get_max_entropy(), 1.0f));
    CHECK(close_to(get_entropy_ratio(), 0.811278f));

    CHECK(close_to(shannon_H(binary, sizeof(binary)), 1.0f));
    CHECK(get_num_tokens() == 2);

    printf("libdisorder API test passed: %d checks\n", checks);
    return 0;
}

