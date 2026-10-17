cmake_minimum_required(VERSION 3.18)
project(test_re C)

find_package(re REQUIRED)

add_executable(test_re test_re.c)
target_link_libraries(test_re PRIVATE re::re)
target_include_directories(test_re PRIVATE ${re_INCLUDE_DIRS})