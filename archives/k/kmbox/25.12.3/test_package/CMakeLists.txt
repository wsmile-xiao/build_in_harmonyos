cmake_minimum_required(VERSION 3.16)
project(test_kmbox LANGUAGES CXX)

find_package(KPim6Mbox CONFIG REQUIRED)
find_package(KPim6Mime CONFIG REQUIRED)
find_package(Qt6 CONFIG REQUIRED COMPONENTS Core)

add_executable(test_kmbox test_kmbox.cpp)
target_link_libraries(test_kmbox PRIVATE KPim6::Mbox KPim6::Mime Qt6::Core)

enable_testing()
add_test(NAME test_kmbox COMMAND test_kmbox)
