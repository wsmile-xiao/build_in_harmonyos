#include <yaml.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    yaml_parser_t parser;
    yaml_token_t token;

    if (!yaml_parser_initialize(&parser)) {
        fprintf(stderr, "Failed to initialize YAML parser\n");
        return 1;
    }

    /* Parse a simple YAML document */
    const char *yaml_doc = "key: value\n";
    yaml_parser_set_input_string(&parser,
        (const unsigned char *)yaml_doc, (size_t)strlen(yaml_doc));

    /* Read first token (STREAM_START) */
    if (!yaml_parser_scan(&parser, &token)) {
        fprintf(stderr, "Failed to scan token\n");
        yaml_parser_delete(&parser);
        return 1;
    }

    if (token.type != YAML_STREAM_START_TOKEN) {
        fprintf(stderr, "Expected STREAM_START, got %d\n", token.type);
        yaml_token_delete(&token);
        yaml_parser_delete(&parser);
        return 1;
    }

    yaml_token_delete(&token);
    yaml_parser_delete(&parser);

    printf("libyaml test: OK\n");
    return 0;
}
