/* Consumer test for cgltf 1.15 — parses a minimal valid glTF JSON. */
#define CGLTF_IMPLEMENTATION
#include "cgltf.h"
#include <stdio.h>
#include <string.h>

static int g_checks = 0;
static int g_failed = 0;
#define CHECK(cond) do { ++g_checks; if (!(cond)) { ++g_failed; printf("FAIL: %s\n", #cond); } } while(0)

int main(void) {
    const char json[] = "{\"asset\":{\"version\":\"2.0\"}}";
    cgltf_options opts;
    memset(&opts, 0, sizeof(opts));
    cgltf_data *data = NULL;
    cgltf_result r = cgltf_parse(&opts, json, (cgltf_size)strlen(json), &data);
    CHECK(r == cgltf_result_success);
    if (data) {
        CHECK(data->asset.version != NULL);
        CHECK(strcmp(data->asset.version, "2.0") == 0);
        cgltf_free(data);
    }
    printf("cgltf test_package: %d checks, %d failed\n", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
