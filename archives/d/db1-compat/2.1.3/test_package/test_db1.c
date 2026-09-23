#include <db.h>
#include <ndbm.h>

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int checks;

#define CHECK(condition, message)                                            \
    do {                                                                     \
        ++checks;                                                            \
        if (!(condition)) {                                                  \
            fprintf(stderr, "FAIL: %s (line %d, errno=%d)\n",              \
                    (message), __LINE__, errno);                             \
            return 1;                                                        \
        }                                                                    \
    } while (0)

static DBT text_dbt(char *value)
{
    DBT item;
    item.data = value;
    item.size = strlen(value) + 1;
    return item;
}

static int data_is(const DBT *item, const char *expected)
{
    return item->size == strlen(expected) + 1 &&
           memcmp(item->data, expected, item->size) == 0;
}

static int test_btree(const char *path)
{
    DB *db;
    DBT key_alpha = text_dbt("alpha");
    DBT key_beta = text_dbt("beta");
    DBT value_one = text_dbt("one");
    DBT value_two = text_dbt("two");
    DBT key;
    DBT value;
    int count = 0;

    db = dbopen(path, O_CREAT | O_TRUNC | O_RDWR, 0600, DB_BTREE, NULL);
    CHECK(db != NULL, "open B-tree database");
    CHECK(db->put(db, &key_alpha, &value_one, 0) == RET_SUCCESS,
          "insert alpha into B-tree");
    CHECK(db->put(db, &key_beta, &value_two, 0) == RET_SUCCESS,
          "insert beta into B-tree");
    CHECK(db->put(db, &key_alpha, &value_two, R_NOOVERWRITE) == RET_SPECIAL,
          "B-tree R_NOOVERWRITE protects existing value");
    CHECK(db->get(db, &key_alpha, &value, 0) == RET_SUCCESS &&
              data_is(&value, "one"),
          "read B-tree value");

    if (db->seq(db, &key, &value, R_FIRST) == RET_SUCCESS) {
        ++count;
        while (db->seq(db, &key, &value, R_NEXT) == RET_SUCCESS)
            ++count;
    }
    CHECK(count == 2, "iterate both B-tree records");
    CHECK(db->del(db, &key_beta, 0) == RET_SUCCESS, "delete B-tree record");
    CHECK(db->sync(db, 0) == RET_SUCCESS, "sync B-tree database");
    CHECK(db->close(db) == RET_SUCCESS, "close B-tree database");

    db = dbopen(path, O_RDWR, 0600, DB_BTREE, NULL);
    CHECK(db != NULL, "reopen B-tree database");
    CHECK(db->get(db, &key_alpha, &value, 0) == RET_SUCCESS &&
              data_is(&value, "one"),
          "B-tree data persists after reopen");
    CHECK(db->get(db, &key_beta, &value, 0) == RET_SPECIAL,
          "deleted B-tree key stays absent");
    CHECK(db->close(db) == RET_SUCCESS, "close reopened B-tree database");
    return 0;
}

static int test_hash(const char *path)
{
    DB *db;
    DBT key = text_dbt("large-key");
    DBT value;
    DBT fetched;
    char *large = malloc(16385);

    CHECK(large != NULL, "allocate large Hash value");
    memset(large, 'H', 16384);
    large[16384] = '\0';
    value = text_dbt(large);

    db = dbopen(path, O_CREAT | O_TRUNC | O_RDWR, 0600, DB_HASH, NULL);
    CHECK(db != NULL, "open Hash database");
    CHECK(db->put(db, &key, &value, 0) == RET_SUCCESS,
          "store overflow-sized Hash value");
    CHECK(db->get(db, &key, &fetched, 0) == RET_SUCCESS &&
              fetched.size == value.size &&
              memcmp(fetched.data, large, value.size) == 0,
          "read overflow-sized Hash value");
    CHECK(db->sync(db, 0) == RET_SUCCESS, "sync Hash database");
    CHECK(db->close(db) == RET_SUCCESS, "close Hash database");

    db = dbopen(path, O_RDWR, 0600, DB_HASH, NULL);
    CHECK(db != NULL, "reopen Hash database");
    CHECK(db->get(db, &key, &fetched, 0) == RET_SUCCESS &&
              fetched.size == value.size,
          "Hash value persists after reopen");
    CHECK(db->del(db, &key, 0) == RET_SUCCESS, "delete Hash record");
    CHECK(db->get(db, &key, &fetched, 0) == RET_SPECIAL,
          "deleted Hash key is absent");
    CHECK(db->close(db) == RET_SUCCESS, "close reopened Hash database");
    free(large);
    return 0;
}

static int test_recno(void)
{
    DB *db = dbopen(NULL, O_RDWR, 0600, DB_RECNO, NULL);
    recno_t number_one = 1;
    recno_t number_two = 2;
    DBT key_one = {&number_one, sizeof(number_one)};
    DBT key_two = {&number_two, sizeof(number_two)};
    DBT line_one = text_dbt("line one");
    DBT line_two = text_dbt("line two");
    DBT key;
    DBT value;
    int count = 0;

    CHECK(db != NULL, "open in-memory Recno database");
    CHECK(db->put(db, &key_one, &line_one, 0) == RET_SUCCESS,
          "store Recno record one");
    CHECK(db->put(db, &key_two, &line_two, 0) == RET_SUCCESS,
          "store Recno record two");
    key_one.data = &number_one;
    key_one.size = sizeof(number_one);
    key_two.data = &number_two;
    key_two.size = sizeof(number_two);
    CHECK(db->get(db, &key_two, &value, 0) == RET_SUCCESS &&
              data_is(&value, "line two"),
          "read Recno record by number");
    if (db->seq(db, &key, &value, R_FIRST) == RET_SUCCESS) {
        ++count;
        while (db->seq(db, &key, &value, R_NEXT) == RET_SUCCESS)
            ++count;
    }
    CHECK(count == 2, "iterate Recno records");
    key_one.data = &number_one;
    key_one.size = sizeof(number_one);
    CHECK(db->del(db, &key_one, 0) == RET_SUCCESS, "delete Recno record");
    key_two.data = &number_two;
    key_two.size = sizeof(number_two);
    CHECK(db->get(db, &key_two, &value, 0) == RET_SPECIAL,
          "Recno indices compact after delete");
    key_one.data = &number_one;
    key_one.size = sizeof(number_one);
    CHECK(db->get(db, &key_one, &value, 0) == RET_SUCCESS &&
              data_is(&value, "line two"),
          "remaining Recno record moves to index one");
    CHECK(db->close(db) == RET_SUCCESS, "close Recno database");
    return 0;
}

static int test_ndbm(const char *base)
{
    DBM *db;
    datum key = {(char *)"fruit", 5};
    datum first = {(char *)"apple", 5};
    datum second = {(char *)"pear", 4};
    datum fetched;
    datum iterated;

    db = dbm_open(base, O_CREAT | O_TRUNC | O_RDWR, 0600);
    CHECK(db != NULL, "open NDBM database");
    CHECK(dbm_store(db, key, first, DBM_INSERT) == RET_SUCCESS,
          "NDBM insert");
    CHECK(dbm_store(db, key, second, DBM_INSERT) == RET_SPECIAL,
          "NDBM insert rejects duplicate");
    CHECK(dbm_store(db, key, second, DBM_REPLACE) == RET_SUCCESS,
          "NDBM replace");
    fetched = dbm_fetch(db, key);
    CHECK(fetched.dptr != NULL && fetched.dsize == second.dsize &&
              memcmp(fetched.dptr, second.dptr, second.dsize) == 0,
          "NDBM fetch replaced value");
    iterated = dbm_firstkey(db);
    CHECK(iterated.dptr != NULL && iterated.dsize == key.dsize,
          "NDBM first-key iteration");
    dbm_close(db);

    db = dbm_open(base, O_RDWR, 0600);
    CHECK(db != NULL, "reopen NDBM database");
    fetched = dbm_fetch(db, key);
    CHECK(fetched.dptr != NULL && fetched.dsize == second.dsize,
          "NDBM data persists after reopen");
    CHECK(dbm_delete(db, key) == RET_SUCCESS, "NDBM delete");
    CHECK(dbm_fetch(db, key).dptr == NULL, "deleted NDBM key is absent");
    CHECK(dbm_error(db) == 0, "NDBM error state remains clear");
    CHECK(dbm_clearerr(db) == 0, "NDBM clear-error succeeds");
    dbm_close(db);
    return 0;
}

static int test_invalid_type(void)
{
    errno = 0;
    CHECK(dbopen(NULL, O_RDWR, 0600, (DBTYPE)99, NULL) == NULL,
          "invalid database type is rejected");
    CHECK(errno == EINVAL, "invalid database type sets EINVAL");
    return 0;
}

int main(void)
{
    char btree_path[96];
    char hash_path[96];
    char ndbm_base[96];
    char ndbm_path[100];

    snprintf(btree_path, sizeof(btree_path), "db1-btree-%ld.db", (long)getpid());
    snprintf(hash_path, sizeof(hash_path), "db1-hash-%ld.db", (long)getpid());
    snprintf(ndbm_base, sizeof(ndbm_base), "db1-ndbm-%ld", (long)getpid());
    snprintf(ndbm_path, sizeof(ndbm_path), "%s.db", ndbm_base);

    if (test_btree(btree_path) || test_hash(hash_path) || test_recno() ||
        test_ndbm(ndbm_base) || test_invalid_type()) {
        unlink(btree_path);
        unlink(hash_path);
        unlink(ndbm_path);
        return 1;
    }

    unlink(btree_path);
    unlink(hash_path);
    unlink(ndbm_path);
    printf("db1-compat API tests passed (%d assertions)\n", checks);
    return 0;
}
