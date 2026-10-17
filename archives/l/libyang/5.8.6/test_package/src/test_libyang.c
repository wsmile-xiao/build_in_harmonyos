/* libyang consumer test.
 *
 * Links the installed libyang and drives the real public API declared in
 * <libyang/libyang.h> (R34: the test must exercise the package under test,
 * not merely link it).
 *
 * The test walks the full pipeline the library exists for: create a context,
 * compile an inline YANG module, parse instance data from JSON, validate it,
 * and check that invalid data is actually rejected (a package that merely
 * links would pass the positive cases and fail the negative ones).
 */

#include <libyang/libyang.h>

#include <stdio.h>
#include <stdlib.h>

/* libyang needs a directory containing its own YANG modules (the ones shipped
 * in the project's modules/ directory and installed next to the library).  The
 * test_package passes its absolute path in as a compile definition. */
#ifndef LIBYANG_MODULES_DIR
#define LIBYANG_MODULES_DIR ""
#endif

static int failures = 0;

static void check(int ok, const char *what)
{
    printf("%s %s\n", ok ? "ok  " : "FAIL", what);
    if (!ok) {
        ++failures;
    }
}

static const char *YANG_MODULE =
    "module conan-test {\n"
    "  yang-version 1.1;\n"
    "  namespace \"urn:conan:test\";\n"
    "  prefix ct;\n"
    "  container top {\n"
    "    leaf name {\n"
    "      type string;\n"
    "    }\n"
    "    leaf count {\n"
    "      type uint32 {\n"
    "        range \"0..100\";\n"
    "      }\n"
    "      mandatory true;\n"
    "    }\n"
    "    list item {\n"
    "      key \"id\";\n"
    "      leaf id {\n"
    "        type string;\n"
    "      }\n"
    "      leaf value {\n"
    "        type int32;\n"
    "      }\n"
    "    }\n"
    "  }\n"
    "}\n";

static const char *VALID_JSON =
    "{\"conan-test:top\":{\"name\":\"hello\",\"count\":42,"
    "\"item\":[{\"id\":\"a\",\"value\":1},{\"id\":\"b\",\"value\":-7}]}}";

int main(void)
{
    struct ly_ctx *ctx = NULL;
    struct lys_module *mod = NULL;
    struct lyd_node *tree = NULL;
    struct lyd_node *bad = NULL;
    LY_ERR err;

    /* 1. context.  The module directory is required: without it libyang
     *    cannot load its internal modules (ietf-inet-types & friends). */
    {
        const char *mods = LIBYANG_MODULES_DIR;
        if (mods[0] == '\0') {
            mods = getenv("LIBYANG_MODULES_DIR");
        }
        check(mods != NULL && mods[0] != '\0',
              "the test was given libyang's YANG module directory");
        err = ly_ctx_new(mods, 0, &ctx);
    }
    check(err == LY_SUCCESS && ctx != NULL, "ly_ctx_new() created a context");
    if (ctx == NULL) {
        return 1;
    }

    /* 2. compile an inline YANG module */
    err = lys_parse_mem(ctx, YANG_MODULE, LYS_IN_YANG, &mod);
    check(err == LY_SUCCESS && mod != NULL, "lys_parse_mem() compiled the YANG module");
    if (mod == NULL) {
        ly_ctx_destroy(ctx);
        return 1;
    }

    /* 3. parse valid instance data from JSON */
    err = lyd_parse_data_mem(ctx, VALID_JSON, LYD_JSON, LYD_PARSE_ONLY | LYD_PARSE_STRICT, 0, &tree);
    check(err == LY_SUCCESS && tree != NULL, "lyd_parse_data_mem() accepted valid JSON data");

    /* 4. the parsed tree validates against the schema.
     *    LYD_VALIDATE_PRESENT restricts validation to the modules whose data is
     *    actually present — without it libyang also validates the internal
     *    ietf-yang-library module, which has mandatory nodes the caller never
     *    supplied. */
    if (tree != NULL) {
        err = lyd_validate_all(&tree, ctx, LYD_VALIDATE_PRESENT, NULL);
        check(err == LY_SUCCESS, "lyd_validate_all() accepted valid data");
    } else {
        check(0, "lyd_validate_all() accepted valid data");
    }

    /* 5. negative: count = 1000 is outside the declared range 0..100 */
    err = lyd_parse_data_mem(ctx, "{\"conan-test:top\":{\"count\":1000}}", LYD_JSON,
                             LYD_PARSE_ONLY, 0, &bad);
    if (err == LY_SUCCESS) {
        err = lyd_validate_all(&bad, ctx, LYD_VALIDATE_PRESENT, NULL);
    }
    check(err != LY_SUCCESS, "out-of-range value is rejected by validation");
    lyd_free_all(bad);

    /* 6. negative: malformed JSON must not parse */
    bad = NULL;
    err = lyd_parse_data_mem(ctx, "{ not json", LYD_JSON, LYD_PARSE_ONLY, 0, &bad);
    check(err != LY_SUCCESS, "malformed JSON is rejected");
    lyd_free_all(bad);

    /* 7. negative: data for a module that is not in the context must be refused
     *    in strict mode */
    bad = NULL;
    err = lyd_parse_data_mem(ctx, "{\"no-such-module:top\":{\"count\":1}}", LYD_JSON,
                             LYD_PARSE_ONLY | LYD_PARSE_STRICT, 0, &bad);
    check(err != LY_SUCCESS, "data without a matching schema is rejected (strict mode)");
    lyd_free_all(bad);

    /* 8. a third consumer can create its own context from the same module text */
    {
        struct ly_ctx *ctx2 = NULL;
        struct lys_module *mod2 = NULL;
        err = ly_ctx_new(LIBYANG_MODULES_DIR, 0, &ctx2);
        if (err == LY_SUCCESS && ctx2 != NULL) {
            err = lys_parse_mem(ctx2, YANG_MODULE, LYS_IN_YANG, &mod2);
        }
        check(err == LY_SUCCESS && mod2 != NULL,
              "a second context compiles the same module independently");
        if (ctx2 != NULL) {
            ly_ctx_destroy(ctx2);
        }
    }

    lyd_free_all(tree);
    ly_ctx_destroy(ctx);

    if (failures != 0) {
        fprintf(stderr, "%d libyang consumer check(s) FAILED\n", failures);
        return 1;
    }
    printf("all libyang consumer checks passed\n");
    return 0;
}
