// SOCI consumer test.
//
// Links the installed soci core + SQLite3 backend and drives the real public
// API declared in <soci/soci.h> (R34: the test must exercise the package under
// test, not merely link it).
//
// It runs an in-memory SQLite database through the whole surface a consumer
// uses: DDL, parameterised inserts via `use`, reads via `into`, a rowset
// iteration, a prepared statement executed repeatedly, and an exception when
// the SQL is wrong.

#include <soci/soci.h>
#include <soci/sqlite3/soci-sqlite3.h>

#include <iostream>
#include <string>
#include <vector>

static int failures = 0;

static void check(bool ok, const char *what)
{
    std::cout << (ok ? "ok   " : "FAIL ") << what << std::endl;
    if (!ok) {
        ++failures;
    }
}

int main()
{
    try {
        // 1. an in-memory database through the SQLite3 backend
        soci::session sql(soci::sqlite3, ":memory:");
        check(true, "session opened on the SQLite3 backend (:memory:)");

        // 2. DDL
        sql << "CREATE TABLE person (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)";
        check(true, "CREATE TABLE executed");

        // 3. parameterised inserts through `use`
        {
            int id = 1;
            std::string name = "Alice";
            int age = 30;
            sql << "INSERT INTO person VALUES (:id, :name, :age)",
                soci::use(id), soci::use(name), soci::use(age);

            id = 2; name = "Bob"; age = 25;
            sql << "INSERT INTO person VALUES (:id, :name, :age)",
                soci::use(id), soci::use(name), soci::use(age);
        }
        check(true, "two rows inserted with bound parameters");

        // 4. a bound read through `into`
        {
            std::string name;
            int age = 0;
            int wanted_id = 1;   // soci::use() deletes the rvalue overload
            sql << "SELECT name, age FROM person WHERE id = :id", soci::into(name),
                soci::into(age), soci::use(wanted_id);
            check(name == "Alice" && age == 30, "SELECT ... into gives Alice/30");
        }

        // 5. a rowset iterates every row in order
        {
            soci::rowset<soci::row> rs = (sql.prepare << "SELECT id, name FROM person ORDER BY id");
            std::vector<int> ids;
            std::vector<std::string> names;
            for (soci::rowset<soci::row>::const_iterator it = rs.begin(); it != rs.end(); ++it) {
                ids.push_back(it->get<int>(0));
                names.push_back(it->get<std::string>(1));
            }
            check(ids.size() == 2 && ids[0] == 1 && ids[1] == 2,
                  "rowset returned both rows in order");
            check(names.size() == 2 && names[0] == "Alice" && names[1] == "Bob",
                  "rowset returned the expected names");
        }

        // 6. a prepared statement reused: `use` binds by reference, so the
        //    statement picks up the new values on every execute
        {
            int id = 3;
            std::string name = "Carol";
            int age = 41;
            soci::statement st = (sql.prepare << "INSERT INTO person VALUES (:id, :name, :age)",
                                  soci::use(id), soci::use(name), soci::use(age));
            st.execute(true);

            id = 4;
            name = "Dave";
            age = 52;
            st.execute(true);

            int count = 0;
            sql << "SELECT COUNT(*) FROM person", soci::into(count);
            check(count == 4, "prepared statement re-executed -> 4 rows");
        }
    } catch (const soci::soci_error &e) {
        std::cerr << "unexpected soci exception: " << e.what() << std::endl;
        check(false, "no soci_error thrown during the happy path");
    } catch (const std::exception &e) {
        std::cerr << "unexpected exception: " << e.what() << std::endl;
        check(false, "no std::exception thrown during the happy path");
    }

    // 7. negative: bad SQL must raise soci_error, not crash
    try {
        soci::session sql(soci::sqlite3, ":memory:");
        sql << "THIS IS NOT SQL";
        check(false, "bad SQL raised soci_error");
    } catch (const soci::soci_error &) {
        check(true, "bad SQL raised soci_error");
    } catch (...) {
        check(false, "bad SQL raised soci_error");
    }

    // 8. negative: reading a column that does not exist raises
    try {
        soci::session sql(soci::sqlite3, ":memory:");
        sql << "CREATE TABLE t (a INTEGER)";
        int v = 0;
        sql << "SELECT missing_column FROM t", soci::into(v);
        check(false, "selecting a missing column raised soci_error");
    } catch (const soci::soci_error &) {
        check(true, "selecting a missing column raised soci_error");
    } catch (...) {
        check(false, "selecting a missing column raised soci_error");
    }

    if (failures != 0) {
        std::cerr << failures << " soci consumer check(s) FAILED" << std::endl;
        return 1;
    }
    std::cout << "all soci consumer checks passed" << std::endl;
    return 0;
}
