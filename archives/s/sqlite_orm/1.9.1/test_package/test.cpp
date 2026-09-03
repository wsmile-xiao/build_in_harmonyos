#include <sqlite_orm/sqlite_orm.h>
#include <iostream>
#include <string>

// R34: 实质调用被测包 API —— 建立内存数据库、建表、插入、查询并校验结果。
int main() {
    using namespace sqlite_orm;
    struct User {
        int id;
        std::string name;
        int age;
    };
    auto storage = make_storage(
        ":memory:",
        make_table("users",
                   make_column("id", &User::id, primary_key()),
                   make_column("name", &User::name),
                   make_column("age", &User::age)));
    storage.sync_schema();
    storage.replace(User{1, "alice", 30});
    storage.replace(User{2, "bob", 25});
    auto all = storage.get_all<User>();
    if (all.size() != 2) {
        std::cerr << "FAIL: expected 2 rows, got " << all.size() << std::endl;
        return 1;
    }
    auto alice = storage.get<User>(1);
    if (alice.name != "alice" || alice.age != 30) {
        std::cerr << "FAIL: unexpected row content" << std::endl;
        return 1;
    }
    std::cout << "test sqlite_orm 1.9.1: OK (rows=" << all.size() << ")" << std::endl;
    return 0;
}