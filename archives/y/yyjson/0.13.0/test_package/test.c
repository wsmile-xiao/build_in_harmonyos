#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "yyjson.h"

int main(void) {
    /* Test 1: Parse and read JSON */
    const char *json_str = "{\"name\":\"yyjson\",\"version\":\"0.13.0\",\"count\":42}";
    yyjson_doc *doc = yyjson_read(json_str, strlen(json_str), 0);
    if (!doc) {
        fprintf(stderr, "FAIL: yyjson_read returned NULL\n");
        return 1;
    }

    yyjson_val *root = yyjson_doc_get_root(doc);
    if (!yyjson_is_obj(root)) {
        fprintf(stderr, "FAIL: root is not object\n");
        yyjson_doc_free(doc);
        return 1;
    }

    /* Test 2: Get string value */
    yyjson_val *name = yyjson_obj_get(root, "name");
    if (!name || !yyjson_is_str(name)) {
        fprintf(stderr, "FAIL: name field missing or not string\n");
        yyjson_doc_free(doc);
        return 1;
    }
    const char *name_str = yyjson_get_str(name);
    if (strcmp(name_str, "yyjson") != 0) {
        fprintf(stderr, "FAIL: name=%s expected yyjson\n", name_str);
        yyjson_doc_free(doc);
        return 1;
    }

    /* Test 3: Get integer value */
    yyjson_val *count = yyjson_obj_get(root, "count");
    if (!count || !yyjson_is_int(count)) {
        fprintf(stderr, "FAIL: count field missing or not int\n");
        yyjson_doc_free(doc);
        return 1;
    }
    int64_t count_val = yyjson_get_int(count);
    if (count_val != 42) {
        fprintf(stderr, "FAIL: count=%lld expected 42\n", (long long)count_val);
        yyjson_doc_free(doc);
        return 1;
    }

    yyjson_doc_free(doc);

    /* Test 4: Mutable document write */
    yyjson_mut_doc *mdoc = yyjson_mut_doc_new(NULL);
    if (!mdoc) {
        fprintf(stderr, "FAIL: yyjson_mut_doc_new returned NULL\n");
        return 1;
    }
    yyjson_mut_val *mroot = yyjson_mut_obj(mdoc);
    yyjson_mut_doc_set_root(mdoc, mroot);
    yyjson_mut_obj_add_str(mdoc, mroot, "status", "ok");
    size_t out_len = 0;
    char *out = yyjson_mut_write(mdoc, 0, &out_len);
    if (!out || strstr(out, "\"ok\"") == NULL) {
        fprintf(stderr, "FAIL: mut_write output unexpected: %s\n", out ? out : "(null)");
        if (out) free(out);
        yyjson_mut_doc_free(mdoc);
        return 1;
    }
    free(out);
    yyjson_mut_doc_free(mdoc);

    printf("All yyjson tests passed\n");
    return 0;
}
