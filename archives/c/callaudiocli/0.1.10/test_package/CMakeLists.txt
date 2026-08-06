cmake_minimum_required(VERSION 3.15)
project(test_callaudiocli C)

# Find both callaudiocli and glib (glib provides headers needed by libcallaudio)
find_package(callaudiocli REQUIRED)
find_package(glib REQUIRED)

add_executable(test_callaudiocli test.c)
target_link_libraries(test_callaudiocli PRIVATE callaudiocli::callaudio glib::glib)

# R34: test calls real libcallaudio API
enable_testing()
add_test(NAME callaudiocli_api_test COMMAND test_callaudiocli)
