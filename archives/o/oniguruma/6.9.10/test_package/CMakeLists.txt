cmake_minimum_required(VERSION 3.15)
project(test_oniguruma C)

find_package(oniguruma REQUIRED)

add_executable(test_oniguruma test.c)
target_link_libraries(test_oniguruma oniguruma::onig)

enable_testing()
add_test(NAME test_oniguruma COMMAND test_oniguruma)
