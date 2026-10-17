cmake_minimum_required(VERSION 3.15)
project(test_termbox C)

find_package(termbox CONFIG REQUIRED)

add_executable(test_api test_api.c)
target_link_libraries(test_api PRIVATE termbox::termbox)

add_executable(test_ohos_pty test_ohos_pty.c)
target_link_libraries(test_ohos_pty PRIVATE termbox::termbox)

enable_testing()
add_test(NAME termbox_api COMMAND test_api)
add_test(NAME termbox_ohos_pty COMMAND test_ohos_pty)
