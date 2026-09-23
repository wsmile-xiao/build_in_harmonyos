#include <mdbx.h>

#include <stdio.h>
#include <string.h>

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

static int delete_result_ok(int rc) {
    return rc == MDBX_SUCCESS || rc == MDBX_RESULT_TRUE;
}

int main(void) {
    const char *database_path = "libmdbx_c_consumer.mdbx";
    const char key_text[] = "alpha";
    const char value_text[] = "one";
    MDBX_env *env = NULL;
    MDBX_txn *txn = NULL;
    MDBX_dbi dbi = 0;
    MDBX_val key = {(void *)key_text, sizeof(key_text) - 1};
    MDBX_val value = {(void *)value_text, sizeof(value_text) - 1};
    MDBX_val found = {NULL, 0};
    int rc;

    rc = mdbx_env_delete(database_path, MDBX_ENV_JUST_DELETE);
    if (!check(delete_result_ok(rc), "remove stale database")) {
        goto cleanup;
    }

    rc = mdbx_env_create(&env);
    if (!check(rc == MDBX_SUCCESS && env != NULL, "create environment")) {
        goto cleanup;
    }

    rc = mdbx_env_set_geometry(env, 0, 0, 64 * 1024 * 1024, -1, -1, -1);
    if (!check(rc == MDBX_SUCCESS, "configure database geometry")) {
        goto cleanup;
    }

    rc = mdbx_env_open(env, database_path, MDBX_NOSUBDIR, 0664);
    if (!check(rc == MDBX_SUCCESS, "open environment")) {
        goto cleanup;
    }

    rc = mdbx_txn_begin(env, NULL, 0, &txn);
    if (!check(rc == MDBX_SUCCESS && txn != NULL, "begin write transaction")) {
        goto cleanup;
    }

    rc = mdbx_dbi_open(txn, NULL, 0, &dbi);
    if (!check(rc == MDBX_SUCCESS, "open unnamed database")) {
        goto cleanup;
    }

    rc = mdbx_put(txn, dbi, &key, &value, MDBX_UPSERT);
    if (!check(rc == MDBX_SUCCESS, "put key and value")) {
        goto cleanup;
    }

    rc = mdbx_txn_commit(txn);
    txn = NULL;
    if (!check(rc == MDBX_SUCCESS, "commit inserted value")) {
        goto cleanup;
    }

    rc = mdbx_txn_begin(env, NULL, MDBX_TXN_RDONLY, &txn);
    if (!check(rc == MDBX_SUCCESS && txn != NULL, "begin read transaction")) {
        goto cleanup;
    }

    rc = mdbx_get(txn, dbi, &key, &found);
    if (!check(rc == MDBX_SUCCESS, "get inserted value")) {
        goto cleanup;
    }
    check(found.iov_len == sizeof(value_text) - 1, "verify value length");
    check(found.iov_len == sizeof(value_text) - 1 && memcmp(found.iov_base, value_text, found.iov_len) == 0,
          "verify value contents");

    rc = mdbx_txn_abort(txn);
    txn = NULL;
    if (!check(rc == MDBX_SUCCESS, "abort read transaction")) {
        goto cleanup;
    }

    rc = mdbx_txn_begin(env, NULL, 0, &txn);
    if (!check(rc == MDBX_SUCCESS && txn != NULL, "begin delete transaction")) {
        goto cleanup;
    }

    rc = mdbx_del(txn, dbi, &key, NULL);
    if (!check(rc == MDBX_SUCCESS, "delete key")) {
        goto cleanup;
    }

    rc = mdbx_txn_commit(txn);
    txn = NULL;
    if (!check(rc == MDBX_SUCCESS, "commit deletion")) {
        goto cleanup;
    }

    rc = mdbx_txn_begin(env, NULL, MDBX_TXN_RDONLY, &txn);
    if (!check(rc == MDBX_SUCCESS && txn != NULL, "begin verification transaction")) {
        goto cleanup;
    }

    rc = mdbx_get(txn, dbi, &key, &found);
    check(rc == MDBX_NOTFOUND, "verify deleted key is absent");

    rc = mdbx_txn_abort(txn);
    txn = NULL;
    if (!check(rc == MDBX_SUCCESS, "abort verification transaction")) {
        goto cleanup;
    }

    rc = mdbx_env_close(env);
    env = NULL;
    if (!check(rc == MDBX_SUCCESS, "close environment")) {
        goto cleanup;
    }

    rc = mdbx_env_delete(database_path, MDBX_ENV_JUST_DELETE);
    check(delete_result_ok(rc), "remove database files");

cleanup:
    if (txn != NULL) {
        (void)mdbx_txn_abort(txn);
    }
    if (env != NULL) {
        (void)mdbx_env_close(env);
    }
    if (failed != 0) {
        (void)mdbx_env_delete(database_path, MDBX_ENV_JUST_DELETE);
    }
    printf("libmdbx C consumer: %d passed, %d failed\n", passed, failed);
    return failed == 0 ? 0 : 1;
}
