// test_package consumer test — exercises real SQLiteCpp API (R34: no empty-shell tests).
// Creates an in-memory database, executes DDL + DML, and verifies query results.
#include <SQLiteCpp/SQLiteCpp.h>
#include <iostream>
#include <string>

int main() {
    try {
        // Open an in-memory database and create a table
        SQLite::Database db(":memory:", SQLite::OPEN_READWRITE | SQLite::OPEN_CREATE);
        db.exec("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)");

        // Insert a row via statement binding
        SQLite::Statement insert(db, "INSERT INTO users (name) VALUES (?)");
        insert.bind(1, "ohos");
        insert.exec();

        // Query it back and verify
        SQLite::Statement query(db, "SELECT name FROM users WHERE id = 1");
        if (!query.executeStep()) {
            std::cerr << "FAIL: no row returned" << std::endl;
            return 1;
        }
        std::string name = query.getColumn(0).getString();
        if (name != "ohos") {
            std::cerr << "FAIL: unexpected name '" << name << "'" << std::endl;
            return 1;
        }
        std::cout << "test sqlitecpp 3.3.3: OK (queried name='" << name << "')" << std::endl;
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "FAIL: exception: " << e.what() << std::endl;
        return 1;
    }
}
