// Upstream replay for cppdb 0.3.1: reimplements the offline-capable
// sqlite paths of upstream test/test_basic.cpp and test/test_backend.cpp
// (CRUD, null bindings, single-row fetch, transactions, pooling) without
// needing mysql/postgresql/odbc servers. Each passing check prints one
// UPSTREAM-OK line; any failure throws and the program exits non-zero.
#include <cppdb/frontend.h>
#include <ctime>
#include <iostream>
#include <sstream>
#include <stdexcept>

#define UCHECK(cond, name) do { \
    if (!(cond)) { \
        std::ostringstream oss; \
        oss << "UPSTREAM-FAIL " << (name) << " (line " << __LINE__ << ")"; \
        throw std::runtime_error(oss.str()); \
    } \
    std::cout << "UPSTREAM-OK " << (name) << std::endl; \
} while (0)

static void use_memory_temp_store(cppdb::session &sql)
{
    // HarmonyOS preflight mounts /tmp read-only; sqlite spills temp
    // tables/indices there by default. Keep everything in memory so no
    // test needs a writable /tmp (no test logic is skipped).
    try {
        sql << "PRAGMA temp_store=MEMORY" << cppdb::exec;
    } catch (cppdb::cppdb_error const &) {}
}

int main(int argc, char **argv) {
    std::string db = "test_upstream.db";
    if (argc >= 2) {
        db = argv[1];
    }
    try {
        // mirrors test_basic.cpp banner: library version query works
        // NOTE: cppdb::version_string() returns `const char *` (not
        // std::string), so check for non-null/non-empty C string.
        UCHECK(cppdb::version_string() && *cppdb::version_string(), "01-version-string");
        cppdb::session sql("sqlite3:db=" + db);
        use_memory_temp_store(sql);
        UCHECK(sql.engine() == "sqlite3", "02-engine-sqlite3");
        try {
            sql << "DROP TABLE replay" << cppdb::exec;
        } catch (cppdb::cppdb_error const &) {}
        sql << "create table replay ( id integer primary key autoincrement not null,"
               " n integer, f real, t timestamp, name text )" << cppdb::exec;
        UCHECK(true, "03-create-table");

        std::tm t;
        std::time_t tt = std::time(0);
        t = *std::localtime(&tt);
        std::string torig = asctime(&t);
        // mirrors test_basic.cpp first insert: bound int/real/time/text
        // NOTE: every statement/result is scoped so its sqlite handle is
        // finalized before DROP TABLE; otherwise sqlite reports
        // "database table is locked" (seen on HarmonyOS preflight).
        {
            cppdb::statement s1 = sql << "insert into replay(n,f,t,name) values(?,?,?,?)"
                                      << 10 << 3.1415926565 << t << "Hello 'World'";
            s1.exec();
            UCHECK(s1.sequence_last("replay_id_seq") == 1, "04-rowid-1");
            UCHECK(s1.affected() == 1, "05-affected-1");
        }
        // mirrors test_basic.cpp second insert: null/not_null bindings
        {
            cppdb::statement s2 = sql << "insert into replay(n,f,t,name) values(?,?,?,?)"
                                      << cppdb::use(10, cppdb::not_null_value)
                                      << cppdb::use(3.1415926565, cppdb::null_value)
                                      << cppdb::use(t, cppdb::not_null_value)
                                      << cppdb::use("Hello 'World'", cppdb::not_null_value)
                                      << cppdb::exec;
            UCHECK(s2.sequence_last("replay_id_seq") == 2, "06-rowid-2");
        }
        // mirrors test_basic.cpp fetch loop with null tags and time check
        {
            cppdb::result res = sql << "select id,n,f,t,name from replay limit 10";
            int n = 0;
            while (res.next()) {
                double f = -1;
                int id = -1, k = -1;
                std::tm atime = std::tm();
                std::string name = "nonset";
                cppdb::null_tag_type tag;
                res >> id >> k >> cppdb::into(f, tag) >> atime >> name;
                if (n == 0) {
                    UCHECK(id == 1 && k == 10 && f == 3.1415926565, "07-row0-values");
                    UCHECK(tag == cppdb::not_null_value, "08-row0-notnull");
                } else {
                    UCHECK(id == 2 && f == -1.0, "09-row1-null-real");
                    UCHECK(tag == cppdb::null_value, "10-row1-null-tag");
                }
                UCHECK(asctime(&atime) == torig, n == 0 ? "11-row0-time" : "11-row1-time");
                UCHECK(name == "Hello 'World'", n == 0 ? "12-row0-text" : "12-row1-text");
                n++;
            }
            UCHECK(n == 2, "13-two-rows");
        }
        // mirrors test_basic.cpp single-row fetch via cppdb::row
        {
            cppdb::result one = sql << "SELECT n FROM replay WHERE id=?" << 1 << cppdb::row;
            UCHECK(!one.empty(), "14-row-not-empty");
        }
        // mirrors test_backend.cpp transaction paths with plain SQL
        sql << "BEGIN" << cppdb::exec;
        sql << "insert into replay(n,f,t,name) values(?,?,?,?)"
            << 99 << 1.5 << t << "tmp" << cppdb::exec;
        sql << "ROLLBACK" << cppdb::exec;
        {
            cppdb::result cnt = sql << "SELECT COUNT(*) FROM replay" << cppdb::row;
            int c = 0;
            cnt >> c;
            UCHECK(c == 2, "15-rollback-discards");
        }
        sql << "BEGIN" << cppdb::exec;
        sql << "insert into replay(n,f,t,name) values(?,?,?,?)"
            << 99 << 1.5 << t << "kept" << cppdb::exec;
        sql << "COMMIT" << cppdb::exec;
        // mirrors test_backend.cpp second-connection visibility.
        // Extra sessions are closed (scope exit) before the final DROP
        // so no open read handle keeps the table locked.
        {
            cppdb::session sql2("sqlite3:db=" + db);
            use_memory_temp_store(sql2);
            cppdb::result cnt2 = sql2 << "SELECT COUNT(*) FROM replay" << cppdb::row;
            int c2 = 0;
            cnt2 >> c2;
            UCHECK(c2 == 3, "16-commit-visible");
        }
        // mirrors the @pool_size variants of run_test_linux_a.sh
        {
            cppdb::session pooled("sqlite3:db=" + db + ";@pool_size=3");
            use_memory_temp_store(pooled);
            cppdb::result cnt3 = pooled << "SELECT COUNT(*) FROM replay" << cppdb::row;
            int c3 = 0;
            cnt3 >> c3;
            UCHECK(c3 == 3, "17-pooled-session");
        }
        // cleanup so re-runs stay idempotent
        sql << "DROP TABLE replay" << cppdb::exec;
        UCHECK(true, "18-drop-table");
    } catch (std::exception const &e) {
        std::cerr << "UPSTREAM-ERROR: " << e.what() << std::endl;
        return 1;
    }
    std::cout << "UPSTREAM-ALL-OK" << std::endl;
    return 0;
}
