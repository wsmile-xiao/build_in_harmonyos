cmake_minimum_required(VERSION 3.15)
project(test_ohos_sigc LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(libsigc-2 REQUIRED)

add_executable(test_ohos_sigc test_ohos.cpp)
target_link_libraries(test_ohos_sigc PRIVATE libsigc-2::libsigc-2)
