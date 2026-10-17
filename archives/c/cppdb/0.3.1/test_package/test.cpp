// Consumer test for cppdb 0.3.1: links the packaged library and
// exercises its public frontend API end to end over sqlite.
// Each passing check prints one CHECK-OK line; any failure throws
// and the program exits non-zero (no silent pass possible).
#include <cppdb/frontend.h>
#include <ctime>
#include <iostream>
#include <sstream>
#include <stdexcept>

#define CHECK(cond, name) do { \
    if (!(cond)) { \
        std::ostringstream oss; \
        oss << "CHECK-FAIL " << (name) << " (line " << __LINE__ << ")"; \
        throw std::runtime_error(oss.str()); \
    } \
    std::cout << "CHECK-OK " << (name) << std::endl; \
} while (0)

int main(int argc, char **argv) {
    std::string db = "test_pkg.db";
    if (argc >= 2) {
        db = argv[1];
    }
    try {
        cppdb::session sql("sqlite3:db=" + db);
        try {
            // HarmonyOS preflight mounts /tmp read-only; keep sqlite temp
            // objects in memory so no writable /tmp is needed.
            sql << "PRAGMA temp_store=MEMORY" << cppdb::exec;
        } catch (cppdb::cppdb_error const &) {}
        CHECK(sql.engine() == "sqlite3", "1-engine-sqlite3");
        try {
            sql << "DROP TABLE pkg" << cppdb::exec;
        } catch (cppdb::cppdb_error const &) {}
        sql << "create table pkg ( id integer primary key autoincrement not null,"
               " n integer, name text )" << cppdb::exec;
        CHECK(true, "2-create-table");

        cppdb::statement ins = sql << "insert into pkg(n,name) values(?,?)"
                                   << 42 << "cppdb" << cppdb::exec;
        CHECK(ins.sequence_last("pkg_id_seq") == 1, "3-rowid-1");
        CHECK(ins.affected() == 1, "4-affected-1");

        sql << "insert into pkg(n,name) values(?,?)" << 7 << "harmony" << cppdb::exec;
        cppdb::result cnt = sql << "SELECT COUNT(*) FROM pkg" << cppdb::row;
        int c = 0;
        cnt >> c;
        CHECK(c == 2, "5-count-2");

        cppdb::result res = sql << "SELECT n,name FROM pkg WHERE id=?" << 2 << cppdb::row;
        int n = 0;
        std::string name;
        res >> n >> name;
        CHECK(n == 7 && name == "harmony", "6-select-values");
    } catch (std::exception const &e) {
        std::cerr << "CONSUMER-ERROR: " << e.what() << std::endl;
        return 1;
    }
    std::cout << "CONSUMER-ALL-OK" << std::endl;
    return 0;
}
