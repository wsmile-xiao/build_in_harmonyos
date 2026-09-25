cmake_minimum_required(VERSION 3.16)
project(test_soci CXX)

set(CMAKE_CXX_STANDARD 17)

enable_testing()

find_package(soci REQUIRED)

add_executable(test_soci src/test_soci.cpp)
# the package links its backends plus the core, and sqlite3 transitively
target_link_libraries(test_soci soci::soci)

add_test(NAME soci_consumer COMMAND test_soci)
