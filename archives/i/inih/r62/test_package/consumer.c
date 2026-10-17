#include <ini.h>

#include <stdio.h>
#include <string.h>

struct parse_state {
    int pairs;
};

static int on_pair(void *context, const char *section,
                   const char *name, const char *value)
{
    struct parse_state *state = (struct parse_state *)context;
    if (strcmp(section, "a") != 0 || strcmp(name, "x") != 0 ||
        value == NULL || strcmp(value, "42") != 0) {
        return 0;
    }
    state->pairs++;
    return 1;
}

int main(void)
{
    const char data[] = {'[', 'a', ']', '\n', 'x', '=', '4', '2', '\n',
                         'y', '=', '9', '\n'};
    struct parse_state state = {0};
    int passed = 0;

    if (ini_parse_string_length(data, 9, on_pair, &state) != 0 ||
        state.pairs != 1) {
        fprintf(stderr, "FAIL bounded string parsing\n");
        return 1;
    }
    passed++;

    state.pairs = 0;
    if (ini_parse_string("[a]\nx=42\n", on_pair, &state) != 0 ||
        state.pairs != 1) {
        fprintf(stderr, "FAIL zero-terminated string parsing\n");
        return 1;
    }
    passed++;

    state.pairs = 0;
    if (ini_parse_string("[broken\n", on_pair, &state) <= 0 ||
        state.pairs != 0) {
        fprintf(stderr, "FAIL malformed section error\n");
        return 1;
    }
    passed++;

    printf("INI_INSTALLED_CONSUMER_PASS %d/3\n", passed);
    return passed == 3 ? 0 : 1;
}
