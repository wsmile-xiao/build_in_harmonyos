#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <rw.h>

#if defined(RW_EXPECT_OHOS) && !defined(__OHOS__)
#error "OHOS consumer validation must be compiled by the OHOS toolchain"
#endif

static int tests_run;
static int assertions_run;

#define CHECK(condition)                                                        \
    do {                                                                        \
        ++assertions_run;                                                       \
        if (!(condition)) {                                                     \
            fprintf(stderr, "check failed at %s:%d: %s\n", __FILE__, __LINE__, \
                    #condition);                                                \
            return 1;                                                           \
        }                                                                       \
    } while (0)

static void set_edge(unsigned int from, unsigned int to)
{
    adjacency_matrix[from] |= (subset_t)1U << to;
    adjacency_matrix[to] |= (subset_t)1U << from;
}

static int begin_graph(unsigned int vertices)
{
    CHECK(init_rw_dec((uint_fast8_t)vertices) == 0);
    memset(adjacency_matrix, 0, sizeof(*adjacency_matrix) * vertices);
    return 0;
}

static int test_single_vertex(void)
{
    CHECK(begin_graph(1) == 0);
    calculate_all();
    CHECK(get_rw() == 0);
    CHECK(cslots[1] == 0);
    destroy_rw();
    return 0;
}

static int test_empty_graph(void)
{
    CHECK(begin_graph(4) == 0);
    calculate_all();
    CHECK(get_rw() == 0);
    destroy_rw();
    return 0;
}

static int test_single_edge(void)
{
    CHECK(begin_graph(2) == 0);
    set_edge(0, 1);
    calculate_all();
    CHECK(get_rw() == 1);
    CHECK(cslots[3] == 1 || cslots[3] == 2);
    destroy_rw();
    return 0;
}

static int test_path_graph(void)
{
    CHECK(begin_graph(4) == 0);
    set_edge(0, 1);
    set_edge(1, 2);
    set_edge(2, 3);
    calculate_all();
    CHECK(get_rw() == 1);
    destroy_rw();
    return 0;
}

static int test_cycle_graph(void)
{
    CHECK(begin_graph(4) == 0);
    set_edge(0, 1);
    set_edge(1, 2);
    set_edge(2, 3);
    set_edge(3, 0);
    calculate_all();
    CHECK(get_rw() == 1);
    destroy_rw();
    return 0;
}

static int test_complete_graph(void)
{
    unsigned int i;
    unsigned int j;

    CHECK(begin_graph(5) == 0);
    for (i = 0; i < 5; ++i)
        for (j = i + 1; j < 5; ++j)
            set_edge(i, j);
    calculate_all();
    CHECK(get_rw() == 1);
    CHECK(cslots[31] != 0);
    destroy_rw();
    return 0;
}

static int test_level_by_level(void)
{
    unsigned int level;

    CHECK(begin_graph(3) == 0);
    set_edge(0, 1);
    set_edge(1, 2);
    for (level = 0; level <= 3; ++level)
        calculate_level((uint_fast8_t)level);
    CHECK(get_rw() == 1);
    CHECK(cslots[7] != 0);
    destroy_rw();
    return 0;
}

static int test_ohos_abi(void)
{
#if defined(RW_EXPECT_OHOS)
    CHECK(sizeof(void *) == 8);
    CHECK(sizeof(subset_t) >= 4);
    CHECK(MAX_VERTICES == 32);
#else
    CHECK(sizeof(subset_t) >= 4);
#endif
    return 0;
}

static int run_test(const char *name, int (*test)(void))
{
    const int result = test();
    ++tests_run;
    if (result != 0) {
        fprintf(stderr, "FAIL: %s\n", name);
        return result;
    }
    printf("PASS: %s\n", name);
    return 0;
}

int main(void)
{
    if (run_test("single vertex", test_single_vertex) ||
        run_test("empty graph", test_empty_graph) ||
        run_test("single edge and decomposition", test_single_edge) ||
        run_test("path graph", test_path_graph) ||
        run_test("cycle graph", test_cycle_graph) ||
        run_test("complete graph", test_complete_graph) ||
        run_test("level-by-level calculation", test_level_by_level) ||
        run_test("HarmonyOS aarch64 ABI", test_ohos_abi))
        return 1;

    printf("rw tests: %d/8 passed (%d assertions)\n", tests_run,
           assertions_run);
    return tests_run == 8 ? 0 : 1;
}
