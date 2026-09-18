// Minimal Berkeley DB C++ API stub for --disable-wallet builds.
// The wallet is disabled so no libdb_cxx symbol is ever referenced at link
// time; wallet headers (wallet/bdb.h) still need the class *declarations*
// to compile the MWEB translation units that pull them in transitively.
// Every class below is defined with just enough surface for bdb.h and
// walletdb.h to parse; method bodies are omitted (never called).
#ifndef DB_CXX_STUB_H
#define DB_CXX_STUB_H

#include <cstddef>
#include <cstdint>

typedef unsigned int u_int32_t;
typedef int32_t db_recno_t;
typedef u_int32_t db_pgno_t;
typedef u_int16_t db_indx_t;

// Common BDB constants referenced by wallet headers.
#define DB_CREATE       0x0000001
#define DB_THREAD       0x0000002
#define DB_INIT_LOCK    0x0000004
#define DB_INIT_LOG     0x0000008
#define DB_INIT_MPOOL   0x0000010
#define DB_INIT_TXN     0x0000020
#define DB_RECOVER      0x0000040
#define DB_RECOVER_FATAL 0x0000080
#define DB_TXN_WRITE_NOSYNC 0x0000100
#define DB_RDONLY       0x0000200
#define DB_EXCL         0x0000400
#define DB_TRUNCATE     0x0000800
#define DB_AUTO_COMMIT  0x0001000
#define DB_DIRECT_DB    0x0002000
#define DB_NOLOCKING    0x0004000
#define DB_DSYNC_DB     0x0008000
#define DB_CXX_NO_EXCEPTIONS 0x0010000
#define DB_FILE_ID_LEN      20      /* Unique file ID length. */

class DbEnv;
class DbTxn;

class Dbt {
public:
    Dbt() {}
    void* get_data() const { return nullptr; }
    u_int32_t get_size() const { return 0; }
    void set_data(void*) {}
    void set_size(u_int32_t) {}
    void set_flags(u_int32_t) {}
    void set_ulen(u_int32_t) {}
};

class Dbc {
public:
    ~Dbc() {}
    int close() { return 0; }
};

class Db {
public:
    Db(DbEnv*, u_int32_t) {}
    int close(u_int32_t) { return 0; }
    int open(DbTxn*, const char*, const char*, int, u_int32_t) { return 0; }
    int get(DbTxn*, Dbt*, Dbt*, u_int32_t) { return 0; }
    int put(DbTxn*, Dbt*, Dbt*, u_int32_t) { return 0; }
    int del(DbTxn*, Dbt*, u_int32_t) { return 0; }
    int cursor(DbTxn*, Dbc**, u_int32_t) { return 0; }
    int stat(DbTxn*, void*, u_int32_t) { return 0; }
};

class DbTxn {
public:
    int abort() { return 0; }
    int commit(u_int32_t) { return 0; }
};

class DbEnv {
public:
    int open(const char*, u_int32_t, int) { return 0; }
    int close(u_int32_t) { return 0; }
    void err(int, const char*, ...) {}
    int txn_begin(DbTxn*, DbTxn**, u_int32_t) { return 0; }
    static int db_version(int*, int*, int*) { return 0; }
    void set_cachesize(u_int32_t, u_int32_t, int) {}
    void set_lk_max_locks(u_int32_t) {}
    void set_flags(u_int32_t, int) {}
};

#endif // DB_CXX_STUB_H
