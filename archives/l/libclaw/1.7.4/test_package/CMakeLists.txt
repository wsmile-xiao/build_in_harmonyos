cmake_minimum_required(VERSION 3.15)

project(test_libclaw CXX)

find_package(libclaw REQUIRED CONFIG)
find_package(Boost REQUIRED CONFIG COMPONENTS thread headers)

add_executable(test_libclaw test_libclaw.cpp)
target_link_libraries(test_libclaw PRIVATE libclaw::libclaw Boost::thread Boost::headers)
target_compile_features(test_libclaw PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_libclaw COMMAND test_libclaw)
