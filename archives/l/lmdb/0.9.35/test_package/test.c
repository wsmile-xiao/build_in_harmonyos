#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/stat.h>
#include <unistd.h>
#include "lmdb.h"

int main(void) {
    MDB_env *env;
    MDB_txn *txn;
    MDB_dbi dbi;
    MDB_val key, data;
    char dbpath[256];
    int rc;

    /* Create a temp directory for the LMDB environment */
    snprintf(dbpath, sizeof(dbpath), "%s/lmdb_test_%d",
             getenv("TMPDIR") ? getenv("TMPDIR") : "/tmp", (int)getpid());
    if (mkdir(dbpath, 0755) != 0 && errno != EEXIST) {
        perror("mkdir");
        return 1;
    }

    rc = mdb_env_create(&env);
    if (rc != MDB_SUCCESS) {
        fprintf(stderr, "mdb_env_create failed: %s\n", mdb_strerror(rc));
        return 1;
    }

    rc = mdb_env_open(env, dbpath, 0, 0664);
    if (rc != MDB_SUCCESS) {
        fprintf(stderr, "mdb_env_open failed: %s\n", mdb_strerror(rc));
        mdb_env_close(env);
        return 1;
    }

    rc = mdb_txn_begin(env, NULL, 0, &txn);
    if (rc != MDB_SUCCESS) {
        fprintf(stderr, "mdb_txn_begin failed: %s\n", mdb_strerror(rc));
        mdb_env_close(env);
        return 1;
    }

    rc = mdb_dbi_open(txn, NULL, 0, &dbi);
    if (rc != MDB_SUCCESS) {
        fprintf(stderr, "mdb_dbi_open failed: %s\n", mdb_strerror(rc));
        mdb_txn_abort(txn);
        mdb_env_close(env);
        return 1;
    }

    /* Put a key-value pair */
    key.mv_size = sizeof("hello") - 1;
    key.mv_data = "hello";
    data.mv_size = sizeof("world") - 1;
    data.mv_data = "world";

    rc = mdb_put(txn, dbi, &key, &data, 0);
    if (rc != MDB_SUCCESS) {
        fprintf(stderr, "mdb_put failed: %s\n", mdb_strerror(rc));
        mdb_txn_abort(txn);
        mdb_env_close(env);
        return 1;
    }

    rc = mdb_txn_commit(txn);
    if (rc != MDB_SUCCESS) {
        fprintf(stderr, "mdb_txn_commit failed: %s\n", mdb_strerror(rc));
        /* txn already invalidated by failed commit, do not abort */
        mdb_env_close(env);
        return 1;
    }

    /* Read back the value */
    rc = mdb_txn_begin(env, NULL, MDB_RDONLY, &txn);
    if (rc != MDB_SUCCESS) {
        fprintf(stderr, "mdb_txn_begin (read) failed: %s\n", mdb_strerror(rc));
        mdb_env_close(env);
        return 1;
    }

    key.mv_size = sizeof("hello") - 1;
    key.mv_data = "hello";
    data.mv_size = 0;
    data.mv_data = NULL;

    rc = mdb_get(txn, dbi, &key, &data);
    if (rc != MDB_SUCCESS) {
        fprintf(stderr, "mdb_get failed: %s\n", mdb_strerror(rc));
        mdb_txn_abort(txn);
        mdb_env_close(env);
        return 1;
    }

    /* Verify the value */
    if (data.mv_size == 5 && strncmp(data.mv_data, "world", 5) == 0) {
        printf("test lmdb 0.9.35: OK (put/get verified)\n");
    } else {
        fprintf(stderr, "test lmdb: value mismatch\n");
        mdb_txn_abort(txn);
        mdb_env_close(env);
        return 1;
    }

    mdb_txn_abort(txn);
    mdb_dbi_close(env, dbi);
    mdb_env_close(env);

    /* Cleanup */
    /* Note: data file and lock file may remain; that's OK for a test */

    return 0;
}