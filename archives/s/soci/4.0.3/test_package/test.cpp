// Consumer test for soci 4.0.3: exercise the packaged soci as a real user —
// open the SQLite3 backend, create/insert/select through the soci session and
// assert the round-trip value. This also proves the packaged shared objects
// (libsoci_core/libsoci_sqlite3/libsqlite3) load and interoperate at runtime.
#include <cstdio>

#include <soci/soci.h>
#include <soci/sqlite3/soci-sqlite3.h>

int main() {
    try {
        soci::session sql(soci::sqlite3, ":memory:");

        sql << "create table t (a integer)";
        sql << "insert into t values (42)";

        int n = -1;
        sql << "select a from t", soci::into(n);

        if (n != 42) {
            std::fprintf(stderr, "FAIL: round-trip mismatch, got %d want 42\n", n);
            return 1;
        }
        std::printf("test soci 4.0.3: sqlite3 in-memory round-trip OK (%d)\n", n);
        return 0;
    } catch (std::exception const &e) {
        std::fprintf(stderr, "FAIL: soci exception: %s\n", e.what());
        return 1;
    }
}
