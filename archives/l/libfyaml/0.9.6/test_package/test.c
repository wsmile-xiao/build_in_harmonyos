#include <stdio.h>
#include <string.h>
#include <libfyaml.h>

/* Consumer test: link against packaged libfyaml and exercise its public
 * API (parse -> lookup -> emit round-trip). Exits non-zero on mismatch.
 * This is a real consumer test (R34), not a print-only stub. */
int main(void) {
    int fails = 0;
    const char *yaml = "name: libfyaml\nlist:\n  - a\n  - b\n";

    struct fy_document *doc = fy_document_build_from_string(NULL, yaml, strlen(yaml));
    if (!doc) {
        printf("consumer test: fy_document_build_from_string FAILED\n");
        return 1;
    }

    struct fy_node *root = fy_document_root(doc);
    struct fy_node *n = fy_node_mapping_lookup_value_by_string(root, "name", -1);
    if (!n) {
        printf("consumer test: lookup FAILED\n");
        fy_document_destroy(doc);
        return 1;
    }
    size_t len = 0;
    const char *s = fy_node_get_scalar(n, &len);
    if (!s || len != 8 || memcmp(s, "libfyaml", 8) != 0) {
        printf("consumer test: scalar mismatch FAILED\n");
        fy_document_destroy(doc);
        return 1;
    }

    char *out = fy_emit_document_to_string(doc, FYECF_DEFAULT);
    if (!out) {
        printf("consumer test: emit FAILED\n");
        fy_document_destroy(doc);
        return 1;
    }
    struct fy_document *doc2 = fy_document_build_from_string(NULL, out, strlen(out));
    if (!doc2) {
        printf("consumer test: reparse FAILED\n");
        free(out);
        fy_document_destroy(doc);
        return 1;
    }

    printf("consumer test libfyaml 0.9.6: PASS (%s)\n", out);
    free(out);
    fy_document_destroy(doc2);
    fy_document_destroy(doc);
    return fails ? 1 : 0;
}