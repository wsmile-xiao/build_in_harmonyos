#include <stdio.h>
#include <string.h>
#include <assert.h>
#include "lwjson/lwjson.h"

/* Consumer test for lwjson 1.9.0 (R34: must exercise the package's real
   public API — parse a business-like JSON config, find keys by path,
   read typed values, iterate an array — not a print-only shell).
   Note: side-effect calls (lwjson_init/parse/free) are kept OUTSIDE
   assert() so they survive -DNDEBUG builds (CI Release). */

static lwjson_token_t g_tokens[160];

int main(void) {
    const char* json =
        "{\"app\":{\"name\":\"harmonyos-app\",\"version\":\"1.9.0\",\"debug\":false,"
        "\"retries\":3,\"ratio\":0.875,"
        "\"servers\":[\"cn-north-1\",\"cn-south-1\",\"cn-east-2\"]}}";

    lwjson_t lwobj;
    lwjsonr_t r = lwjson_init(&lwobj, g_tokens, sizeof(g_tokens) / sizeof(g_tokens[0]));
    assert(r == lwjsonOK);
    r = lwjson_parse(&lwobj, json);
    assert(r == lwjsonOK);

    /* find by dotted path */
    const lwjson_token_t* tok = lwjson_find(&lwobj, "app.name");
    assert(tok != NULL);
    assert(tok->type == LWJSON_TYPE_STRING);
    size_t name_len = 0;
    const char* name = lwjson_get_val_string(tok, &name_len);
    assert(name != NULL);
    const char* expected_name = "harmonyos-app"; /* 13 chars */
    assert(name_len == strlen(expected_name));
    assert(memcmp(name, expected_name, name_len) == 0);

    tok = lwjson_find(&lwobj, "app.version");
    assert(tok != NULL && tok->type == LWJSON_TYPE_STRING);
    assert(lwjson_get_val_string_length(tok) == strlen("1.9.0"));

    tok = lwjson_find(&lwobj, "app.retries");
    assert(tok != NULL && tok->type == LWJSON_TYPE_NUM_INT);
    assert(lwjson_get_val_int(tok) == 3);

    tok = lwjson_find(&lwobj, "app.ratio");
    assert(tok != NULL && tok->type == LWJSON_TYPE_NUM_REAL);
    double ratio = (double)lwjson_get_val_real(tok);
    assert(ratio > 0.87 && ratio < 0.88);

    tok = lwjson_find(&lwobj, "app.debug");
    assert(tok != NULL && tok->type == LWJSON_TYPE_FALSE);

    /* iterate the servers array via public macros */
    tok = lwjson_find(&lwobj, "app.servers");
    assert(tok != NULL && tok->type == LWJSON_TYPE_ARRAY);
    const lwjson_token_t* child = lwjson_get_first_child(tok);
    int count = 0;
    while (child != NULL) {
        assert(child->type == LWJSON_TYPE_STRING);
        size_t clen = 0;
        const char* cval = lwjson_get_val_string(child, &clen);
        assert(cval != NULL && clen > 0);
        ++count;
        child = child->next;
    }
    assert(count == 3);

    lwjson_free(&lwobj);
    printf("lwjson consumer test: parse/find/typed-value/array-iterate ALL PASS\n");
    return 0;
}