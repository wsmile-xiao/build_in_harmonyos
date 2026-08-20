cmake_minimum_required(VERSION 3.15)
project(test_ki18n CXX)

find_package(KF6I18n REQUIRED)

add_executable(test_ki18n test.cpp)
target_link_libraries(test_ki18n KF6::I18n)

enable_testing()
add_test(NAME test_ki18n COMMAND test_ki18n)
