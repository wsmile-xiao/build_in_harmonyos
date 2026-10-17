cmake_minimum_required(VERSION 3.15)
project(test_libmmmulti CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)

find_package(libmmmulti REQUIRED)

add_executable(test_libmmmulti src/test_package.cpp)
target_link_libraries(test_libmmmulti libmmmulti::libmmmulti Threads::Threads)

enable_testing()
add_test(NAME test_libmmmulti COMMAND test_libmmmulti)
