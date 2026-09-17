cmake_minimum_required(VERSION 3.15)
project(test_libkylin_chkname LANGUAGES CXX)

find_package(libkylin-chkname CONFIG REQUIRED)

add_executable(test_libkylin_chkname test_libkylin_chkname.cpp)
target_compile_features(test_libkylin_chkname PRIVATE cxx_std_11)
target_link_libraries(
    test_libkylin_chkname
    PRIVATE libkylin-chkname::libkylin-chkname
)

enable_testing()
add_test(NAME libkylin_chkname_api COMMAND test_libkylin_chkname)
