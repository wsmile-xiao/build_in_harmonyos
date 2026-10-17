cmake_minimum_required(VERSION 3.16)
project(db1_compat_test C)

find_package(db1-compat CONFIG REQUIRED)

add_executable(db1_api_test test_db1.c)
target_link_libraries(db1_api_test PRIVATE db1-compat::db1-compat)
set_target_properties(db1_api_test PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED ON)

add_executable(db1_ohos_test test_ohos.c)
target_link_libraries(db1_ohos_test PRIVATE db1-compat::db1-compat)
set_target_properties(db1_ohos_test PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED ON)
