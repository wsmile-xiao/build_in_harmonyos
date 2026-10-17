/* Consumer test for libyang — exercises the real public API end to end:
 * context lifecycle, version identity, in-memory YANG schema parsing, JSON
 * data parsing + validation, and data printing. Every CHECK must hold;
 * exit code is nonzero on the first failure so ctest reports it as failed.
 */
#include <stdio.h>
#include <string.h>

#include <libyang/libyang.h>
#include <libyang/version.h>

static const char *smoke_schema =
        "module hmbs-smoke {\n"
        "  yang-version 1.1;\n"
        "  namespace \"urn:hmbs:smoke\";\n"
        "  prefix \"smoke\";\n"
        "  container system {\n"
        "    leaf hostname {\n"
        "      type string;\n"
        "    }\n"
        "  }\n"
        "}\n";

static const char *smoke_data =
        "{\"hmbs-smoke:system\":{\"hostname\":\"harmony\"}}";

static int checks_passed;
static int checks_total;

#define CHECK(cond, label) \
    do { \
        checks_total++; \
        if (cond) { \
            checks_passed++; \
            printf("PASS: %s\n", label); \
        } else { \
            printf("FAIL: %s\n", label); \
            return 1; \
        } \
    } while (0)

int
main(void)
{
    struct ly_ctx *ctx = NULL;
    const struct lys_module *mod = NULL;
    struct lyd_node *tree = NULL;
    char *printed = NULL;

    /* 1-2: context lifecycle + version identity (project 3.13.6). */
    CHECK(ly_ctx_new(NULL, 0, &ctx) == LY_SUCCESS && ctx != NULL, "ly_ctx_new");
    CHECK(strcmp(LY_PROJ_VERSION, "3.13.6") == 0 &&
            strcmp(ly_version_proj_str(), LY_PROJ_VERSION) == 0,
            "version identity");

    /* 3-4: parse an in-memory YANG module, verify its identity. */
    CHECK(lys_parse_mem(ctx, smoke_schema, LYS_IN_YANG, (struct lys_module **)&mod)
            == LY_SUCCESS && mod != NULL, "lys_parse_mem");
    CHECK(strcmp(mod->name, "hmbs-smoke") == 0, "module name");

    /* 5: parse + validate JSON instance data against the schema. */
    CHECK(lyd_parse_data_mem(ctx, smoke_data, LYD_JSON, 0,
            LYD_VALIDATE_PRESENT, &tree) == LY_SUCCESS && tree != NULL,
            "lyd_parse_data_mem");

    /* 6: print the data tree back and confirm the payload survived. */
    CHECK(lyd_print_mem(&printed, tree, LYD_JSON, 0) == LY_SUCCESS &&
            printed != NULL && strstr(printed, "harmony") != NULL,
            "lyd_print_mem round-trip");

    free(printed);
    lyd_free_all(tree);
    ly_ctx_destroy(ctx);

    printf("libyang consumer: %d/%d checks passed\n", checks_passed, checks_total);
    return 0;
}
