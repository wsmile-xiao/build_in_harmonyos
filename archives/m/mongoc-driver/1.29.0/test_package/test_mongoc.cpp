/*
 * mongoc-driver consumer smoke test — initialize/cleanup the driver
 * and create a BSON document to verify the library works.
 */
#include <mongoc/mongoc.h>
#include <bson/bson.h>
#include <stdio.h>

int main(void) {
    /* Initialize the mongoc driver */
    mongoc_init();

    /* Create a BSON document */
    bson_t *doc = BCON_NEW(
        "name", BCON_UTF8("OpenHarmony"),
        "version", BCON_UTF8("1.29.0"),
        "arch", BCON_UTF8("aarch64"));

    if (!doc) {
        fprintf(stderr, "Failed to create BSON document\n");
        mongoc_cleanup();
        return 1;
    }

    /* Convert to JSON for verification */
    size_t json_len;
    char *json = bson_as_json(doc, &json_len);
    if (json) {
        printf("BSON document: %s\n", json);
        bson_free(json);
    } else {
        fprintf(stderr, "Failed to convert BSON to JSON\n");
        bson_destroy(doc);
        mongoc_cleanup();
        return 1;
    }

    bson_destroy(doc);
    mongoc_cleanup();

    printf("mongoc-driver smoke test OK\n");
    return 0;
}
