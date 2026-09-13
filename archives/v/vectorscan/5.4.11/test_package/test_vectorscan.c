#include <hs.h>

#include <stdio.h>
#include <string.h>

struct match_state {
    unsigned int count;
    unsigned long long last_to;
};

static int on_match(unsigned int id,
                    unsigned long long from,
                    unsigned long long to,
                    unsigned int flags,
                    void *context) {
    struct match_state *state = (struct match_state *)context;
    (void)id;
    (void)from;
    (void)flags;
    state->count += 1;
    state->last_to = to;
    return 0;
}

static int require_true(int condition, const char *message) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

int main(void) {
    hs_database_t *database = NULL;
    hs_scratch_t *scratch = NULL;
    hs_compile_error_t *compile_error = NULL;
    struct match_state state = {0, 0};
    const char *input = "foo";
    int failures = 0;

    hs_error_t result = hs_compile(
        "foo", 0, HS_MODE_BLOCK, NULL, &database, &compile_error);
    failures += require_true(result == HS_SUCCESS, "hs_compile succeeds");
    if (compile_error != NULL) {
        fprintf(stderr, "compile error: %s\n", compile_error->message);
        hs_free_compile_error(compile_error);
    }
    if (failures != 0) {
        return failures;
    }

    result = hs_alloc_scratch(database, &scratch);
    failures += require_true(result == HS_SUCCESS, "hs_alloc_scratch succeeds");
    if (failures == 0) {
        result = hs_scan(database, input, (unsigned int)strlen(input), 0,
                         scratch, on_match, &state);
        failures += require_true(result == HS_SUCCESS, "hs_scan succeeds");
    }
    failures += require_true(state.count == 1, "one match callback is delivered");
    failures += require_true(state.last_to == 3, "match ends at input length");

    hs_free_scratch(scratch);
    hs_free_database(database);
    if (failures == 0) {
        puts("vectorscan consumer checks: 5/5 passed");
    }
    return failures;
}
