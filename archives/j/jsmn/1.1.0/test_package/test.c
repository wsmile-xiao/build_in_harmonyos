#include <stdio.h>
#include <string.h>

#include <jsmn.h>

static int token_equals(const char *json, const jsmntok_t *token, const char *value) {
    size_t expected = strlen(value);
    size_t actual = (size_t)(token->end - token->start);
    return actual == expected && strncmp(json + token->start, value, expected) == 0;
}

int main(void) {
    const char *json = "{\"name\":\"OpenHarmony\",\"versions\":[1,1,0],\"stable\":true}";
    jsmn_parser parser;
    jsmntok_t tokens[16];

    jsmn_init(&parser);
    int count = jsmn_parse(&parser, json, strlen(json), tokens, 16);
    if (count != 10) {
        fprintf(stderr, "expected 10 tokens, got %d\n", count);
        return 1;
    }

    if (tokens[0].type != JSMN_OBJECT || tokens[0].size != 3) {
        fprintf(stderr, "root token is not a 3-field object\n");
        return 1;
    }
    if (tokens[1].type != JSMN_STRING || !token_equals(json, &tokens[1], "name")) {
        fprintf(stderr, "missing name key token\n");
        return 1;
    }
    if (tokens[2].type != JSMN_STRING || !token_equals(json, &tokens[2], "OpenHarmony")) {
        fprintf(stderr, "missing name value token\n");
        return 1;
    }
    if (tokens[4].type != JSMN_ARRAY || tokens[4].size != 3) {
        fprintf(stderr, "versions token is not a 3-item array\n");
        return 1;
    }
    if (tokens[5].type != JSMN_PRIMITIVE || !token_equals(json, &tokens[5], "1")) {
        fprintf(stderr, "versions[0] token mismatch\n");
        return 1;
    }
    if (tokens[9].type != JSMN_PRIMITIVE || !token_equals(json, &tokens[9], "true")) {
        fprintf(stderr, "stable token mismatch\n");
        return 1;
    }

    jsmn_init(&parser);
    int small_count = jsmn_parse(&parser, json, strlen(json), tokens, 3);
    if (small_count != JSMN_ERROR_NOMEM) {
        fprintf(stderr, "expected JSMN_ERROR_NOMEM, got %d\n", small_count);
        return 1;
    }

    printf("test jsmn 1.1.0: PASS\n");
    return 0;
}
