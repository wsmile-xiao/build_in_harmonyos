cmake_minimum_required(VERSION 3.16)
project(test_khealthcertificate LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core)
find_package(KHealthCertificate REQUIRED)

add_executable(test_khealthcertificate test.cpp)
target_link_libraries(test_khealthcertificate PRIVATE
    Qt6::Core
    KHealthCertificate
)

enable_testing()
add_test(NAME test_khealthcertificate COMMAND test_khealthcertificate)
