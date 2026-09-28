#include <stdio.h>
#include <string.h>
#include "yyjson.h"

int main(void) {
    /* Parse a JSON string */
    const char *json_str = "{\"name\":\"yyjson\",\"version\":\"0.10.0\",\"features\":[\"reader\",\"writer\",\"utils\"]}";
    yyjson_doc *doc = yyjson_read(json_str, strlen(json_str), 0);
    if (!doc) {
        printf("FAIL: yyjson_read returned NULL\n");
        return 1;
    }

    yyjson_val *root = yyjson_doc_get_root(doc);
    if (!root || !yyjson_is_obj(root)) {
        printf("FAIL: root is not an object\n");
        yyjson_doc_free(doc);
        return 1;
    }

    /* Read "name" field */
    yyjson_val *name_val = yyjson_obj_get(root, "name");
    if (!name_val || !yyjson_is_str(name_val)) {
        printf("FAIL: 'name' field not found or not a string\n");
        yyjson_doc_free(doc);
        return 1;
    }
    const char *name = yyjson_get_str(name_val);
    if (strcmp(name, "yyjson") != 0) {
        printf("FAIL: name='%s', expected 'yyjson'\n", name);
        yyjson_doc_free(doc);
        return 1;
    }

    /* Read "features" array */
    yyjson_val *features = yyjson_obj_get(root, "features");
    if (!features || !yyjson_is_arr(features)) {
        printf("FAIL: 'features' field not found or not an array\n");
        yyjson_doc_free(doc);
        return 1;
    }
    size_t count = yyjson_arr_size(features);
    if (count != 3) {
        printf("FAIL: features count=%zu, expected 3\n", count);
        yyjson_doc_free(doc);
        return 1;
    }

    /* Write JSON back to string */
    size_t written_len = 0;
    char *written = yyjson_write(doc, YYJSON_WRITE_PRETTY, &written_len);
    if (!written || written_len == 0) {
        printf("FAIL: yyjson_write returned NULL\n");
        yyjson_doc_free(doc);
        return 1;
    }

    /* Mutable document test */
    yyjson_mut_doc *mdoc = yyjson_mut_doc_new(NULL);
    yyjson_mut_val *mroot = yyjson_mut_obj(mdoc);
    yyjson_mut_doc_set_root(mdoc, mroot);
    yyjson_mut_obj_add_str(mdoc, mroot, "status", "ok");
    char *mut_written = yyjson_mut_write(mdoc, 0, NULL);
    if (!mut_written) {
        printf("FAIL: yyjson_mut_write returned NULL\n");
        yyjson_mut_doc_free(mdoc);
        free(written);
        yyjson_doc_free(doc);
        return 1;
    } else {
        if (strstr(mut_written, "ok") == NULL) {
            printf("FAIL: mutable write does not contain 'ok'\n");
            free(mut_written);
            yyjson_mut_doc_free(mdoc);
            yyjson_doc_free(doc);
            free(written);
            return 1;
        }
        free(mut_written);
    }
    yyjson_mut_doc_free(mdoc);

    free(written);
    yyjson_doc_free(doc);

    printf("PASS: yyjson 0.10.0 read/write/mut API test OK\n");
    return 0;
}
