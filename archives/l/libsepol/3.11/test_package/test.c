#include <sepol/sepol.h>
#include <sepol/handle.h>
#include <sepol/cil/cil.h>   /* 3.11: CIL header must ship with the package (secilc consumer) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

/* Test: verify handle creation and destruction */
static void test_handle_lifecycle(void)
{
    sepol_handle_t *h = sepol_handle_create();
    assert(h != NULL);
    printf("OK: sepol_handle_create() = %p\n", (void*)h);

    sepol_set_disable_dontaudit(h, 1);
    int val = sepol_get_disable_dontaudit(h);
    assert(val == 1);
    printf("OK: sepol_set/get_disable_dontaudit(1) = %d\n", val);

    sepol_set_disable_dontaudit(h, 0);
    val = sepol_get_disable_dontaudit(h);
    assert(val == 0);
    printf("OK: sepol_set/get_disable_dontaudit(0) = %d\n", val);

    sepol_set_preserve_tunables(h, 1);
    val = sepol_get_preserve_tunables(h);
    assert(val == 1);
    printf("OK: sepol_set/get_preserve_tunables(1) = %d\n", val);

    sepol_handle_destroy(h);
    printf("OK: sepol_handle_destroy()\n");
}

/* Test: verify boolean record operations */
static void test_boolean_record(sepol_handle_t *h)
{
    sepol_bool_t *rec = NULL;
    int rc;

    rc = sepol_bool_create(h, &rec);
    assert(rc == 0);
    assert(rec != NULL);
    printf("OK: sepol_bool_create() = %p\n", (void*)rec);

    rc = sepol_bool_set_name(h, rec, "test_bool");
    assert(rc == 0);

    const char *name = sepol_bool_get_name(rec);
    assert(name != NULL);
    assert(strcmp(name, "test_bool") == 0);
    printf("OK: sepol_bool_get/set_name = '%s'\n", name);

    sepol_bool_set_value(rec, 1);
    int val = sepol_bool_get_value(rec);
    assert(val == 1);
    printf("OK: sepol_bool_get/set_value = %d\n", val);

    sepol_bool_free(rec);
    printf("OK: sepol_bool_free()\n");
}

/* Test: verify context record operations */
static void test_context_record(sepol_handle_t *h)
{
    sepol_context_t *ctx = NULL;
    char *str = NULL;
    int rc;

    rc = sepol_context_create(h, &ctx);
    assert(rc == 0);
    assert(ctx != NULL);
    printf("OK: sepol_context_create() = %p\n", (void*)ctx);

    rc = sepol_context_set_user(h, ctx, "system_u");
    assert(rc == 0);
    rc = sepol_context_set_role(h, ctx, "object_r");
    assert(rc == 0);
    rc = sepol_context_set_type(h, ctx, "test_t");
    assert(rc == 0);
    rc = sepol_context_set_mls(h, ctx, "s0");
    assert(rc == 0);

    const char *user = sepol_context_get_user(ctx);
    const char *role = sepol_context_get_role(ctx);
    const char *type = sepol_context_get_type(ctx);
    const char *mls = sepol_context_get_mls(ctx);
    assert(strcmp(user, "system_u") == 0);
    assert(strcmp(role, "object_r") == 0);
    assert(strcmp(type, "test_t") == 0);
    assert(strcmp(mls, "s0") == 0);
    printf("OK: sepol_context fields: %s:%s:%s:%s\n", user, role, type, mls);

    rc = sepol_context_to_string(h, ctx, &str);
    assert(rc == 0);
    assert(str != NULL);
    assert(strcmp(str, "system_u:object_r:test_t:s0") == 0);
    printf("OK: sepol_context_to_string() = '%s'\n", str);
    free(str);

    sepol_context_free(ctx);
    printf("OK: sepol_context_free()\n");
}

int main(void)
{
    sepol_handle_t *h = NULL;

    printf("=== libsepol API behavior tests ===\n\n");

    h = sepol_handle_create();
    assert(h != NULL);

    test_handle_lifecycle();
    test_boolean_record(h);
    test_context_record(h);

    sepol_handle_destroy(h);

    printf("\n=== All libsepol API behavior tests PASSED ===\n");
    return 0;
}