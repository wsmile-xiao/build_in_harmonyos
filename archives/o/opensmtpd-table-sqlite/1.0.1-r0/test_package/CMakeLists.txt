cmake_minimum_required(VERSION 3.15)
project(test_opensmtpd_table_sqlite C)

# Find both opensmtpd-table-sqlite (the tested package) and sqlite3 (transitive dep)
find_package(opensmtpd-table-sqlite REQUIRED)
find_package(sqlite3 REQUIRED)

add_executable(test_opensmtpd_table_sqlite test.c)
# Link sqlite3 (transitive dependency of opensmtpd-table-sqlite)
target_link_libraries(test_opensmtpd_table_sqlite PRIVATE sqlite3::sqlite3)

enable_testing()
add_test(NAME test_opensmtpd_table_sqlite COMMAND test_opensmtpd_table_sqlite)
