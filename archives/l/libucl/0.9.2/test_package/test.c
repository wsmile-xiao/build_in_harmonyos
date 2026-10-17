#include <stdio.h>
#include <string.h>

#include "ucl.h"

int main(void) {
    const char input[] = "answer = 42; enabled = true;";
    struct ucl_parser *parser = ucl_parser_new(0);
    if (parser == NULL || !ucl_parser_add_chunk(parser,
            (const unsigned char *)input, strlen(input))) {
        ucl_parser_free(parser);
        return 1;
    }

    ucl_object_t *root = ucl_parser_get_object(parser);
    const ucl_object_t *answer = ucl_object_lookup(root, "answer");
    const ucl_object_t *enabled = ucl_object_lookup(root, "enabled");
    int ok = answer != NULL && enabled != NULL &&
             ucl_object_toint(answer) == 42 && ucl_object_toboolean(enabled);

    ucl_object_unref(root);
    ucl_parser_free(parser);
    puts(ok ? "libucl consumer test: OK" : "libucl consumer test: FAIL");
    return ok ? 0 : 1;
}
