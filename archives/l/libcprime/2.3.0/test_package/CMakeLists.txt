cmake_minimum_required(VERSION 3.16)
project(test_libcprime LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core Gui Widgets)

add_executable(test_libcprime main.cpp)
target_link_libraries(test_libcprime PRIVATE Qt6::Core Qt6::Gui Qt6::Widgets)

target_include_directories(test_libcprime PRIVATE "${LIBCPRIME_INCLUDE_DIR}")
target_link_directories(test_libcprime PRIVATE "${LIBCPRIME_LIB_DIR}")
target_link_libraries(test_libcprime PRIVATE cprime)

enable_testing()
add_test(NAME test_libcprime COMMAND test_libcprime)
