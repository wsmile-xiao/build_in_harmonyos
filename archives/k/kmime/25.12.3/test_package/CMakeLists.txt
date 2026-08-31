cmake_minimum_required(VERSION 3.15)
project(test_kmime CXX)

find_package(KPim6Mime 6.6.3 CONFIG REQUIRED)

add_executable(test_kmime test.cpp)
target_link_libraries(test_kmime KPim6::Mime)

enable_testing()
add_test(NAME test_kmime COMMAND test_kmime)
