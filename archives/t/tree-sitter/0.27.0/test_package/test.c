#include <stdio.h>
#include <tree_sitter/api.h>

int main(void) {
    TSParser *parser = ts_parser_new();
    if (!parser) {
        fprintf(stderr, "ERROR: ts_parser_new() returned NULL\n");
        return 1;
    }
    ts_parser_delete(parser);
    printf("test tree-sitter 0.27.0: OK\n");
    return 0;
}
