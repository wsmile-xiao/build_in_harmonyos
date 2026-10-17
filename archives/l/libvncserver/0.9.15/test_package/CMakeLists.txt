cmake_minimum_required(VERSION 3.15)
project(test_libvncserver LANGUAGES C)

find_package(LibVNCServer CONFIG REQUIRED)

add_executable(test_libvncserver test.c)
target_link_libraries(test_libvncserver PRIVATE LibVNCServer::vncserver LibVNCServer::vncclient)

enable_testing()
add_test(NAME test_libvncserver COMMAND test_libvncserver)
