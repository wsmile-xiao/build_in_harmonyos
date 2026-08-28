cmake_minimum_required(VERSION 3.16)
project(test_akonadi CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Sql DBus)
find_package(KPim6Akonadi REQUIRED)

add_executable(test_akonadi test_akonadi.cpp)
target_link_libraries(test_akonadi PRIVATE KPim6::AkonadiCore Qt6::Sql Qt6::DBus)

enable_testing()
add_test(NAME test_akonadi COMMAND test_akonadi)
