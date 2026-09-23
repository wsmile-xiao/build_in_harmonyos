cmake_minimum_required(VERSION 3.15)
project(test_lazperf CXX)

# Package found through the Conan-generated CMakeDeps config
find_package(lazperf REQUIRED)
# std::thread (场景四：多线程压缩确定性)
find_package(Threads REQUIRED)

add_executable(test_lazperf test_lazperf.cpp)
target_link_libraries(test_lazperf PRIVATE lazperf::lazperf Threads::Threads)
set_target_properties(test_lazperf PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_lazperf COMMAND test_lazperf)
