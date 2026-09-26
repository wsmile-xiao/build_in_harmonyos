cmake_minimum_required(VERSION 3.15)
project(test_kfr CXX)

# kfr 7.x raises the requirement to C++20 through
# target_compile_features(kfr INTERFACE cxx_std_20); state it here too so the
# consumer cannot accidentally be compiled at a lower level than the headers.
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(kfr REQUIRED)

add_executable(test_kfr test_kfr.cpp)
target_link_libraries(test_kfr kfr::kfr)

enable_testing()
add_test(NAME test_kfr COMMAND test_kfr)
