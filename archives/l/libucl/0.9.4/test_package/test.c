#include <stdio.h>
#include <stdlib.h>
#include <ucl.h>

int main(void) {
    /* Basic smoke test: parse a simple UCL string */
    struct ucl_parser *parser = ucl_parser_new(0);
    const char *data = "key = \"value\";";

    if (!ucl_parser_add_string(parser, data, 0)) {
        fprintf(stderr, "Failed to parse UCL: %s\n", ucl_parser_get_error(parser));
        ucl_parser_free(parser);
        return 1;
    }

    ucl_object_t *obj = ucl_parser_get_object(parser);
    if (obj == NULL) {
        fprintf(stderr, "Failed to get UCL object\n");
        ucl_parser_free(parser);
        return 1;
    }

    ucl_object_unref(obj);
    ucl_parser_free(parser);

    printf("test libucl 0.9.4: OK\n");
    return 0;
}
