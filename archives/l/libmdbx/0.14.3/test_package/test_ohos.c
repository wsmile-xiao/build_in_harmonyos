#include <mdbx.h>

#include <stdio.h>

static int passed;
static int failed;

static int check(int condition, const char *label) {
    if (condition) {
        ++passed;
        printf("PASS: %s\n", label);
        return 1;
    }
    ++failed;
    fprintf(stderr, "FAIL: %s\n", label);
    return 0;
}

int main(void) {
    const char *database_path = "libmdbx_ohos_hmdfs.mdbx";
    MDBX_env *env = NULL;
    int rc;

    (void)mdbx_env_delete(database_path, MDBX_ENV_JUST_DELETE);

    rc = mdbx_env_create(&env);
    if (!check(rc == MDBX_SUCCESS && env != NULL,
               "create HarmonyOS HMDFS environment")) {
        goto cleanup;
    }

    rc = mdbx_env_set_geometry(env, 0, 0, 64 * 1024 * 1024, -1, -1, -1);
    if (!check(rc == MDBX_SUCCESS, "configure HarmonyOS HMDFS geometry")) {
        goto cleanup;
    }

    rc = mdbx_env_open(env, database_path, MDBX_NOSUBDIR, 0664);
    if (!check(rc == MDBX_SUCCESS,
               "open environment through HarmonyOS HMDFS fallback")) {
        goto cleanup;
    }

    rc = mdbx_env_close(env);
    env = NULL;
    if (!check(rc == MDBX_SUCCESS, "close HarmonyOS HMDFS environment")) {
        goto cleanup;
    }

    rc = mdbx_env_delete(database_path, MDBX_ENV_JUST_DELETE);
    check(rc == MDBX_SUCCESS || rc == MDBX_RESULT_TRUE,
          "remove HarmonyOS HMDFS database files");

cleanup:
    if (env != NULL) {
        (void)mdbx_env_close(env);
    }
    if (failed != 0) {
        (void)mdbx_env_delete(database_path, MDBX_ENV_JUST_DELETE);
    }
    printf("libmdbx HarmonyOS consumer: %d passed, %d failed\n", passed, failed);
    return failed == 0 ? 0 : 1;
}
