cmake_minimum_required(VERSION 3.15)
project(test_kauth CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KF6Auth REQUIRED)

add_executable(test_kauth test.cpp)
target_link_libraries(test_kauth KF6::AuthCore)

foreach(runtime_lib_dir IN LISTS CONAN_RUNTIME_LIB_DIRS)
    target_link_options(test_kauth PRIVATE "-Wl,-rpath,${runtime_lib_dir}")
endforeach()
target_link_options(test_kauth PRIVATE "-Wl,--disable-new-dtags")

enable_testing()
add_test(NAME test_kauth COMMAND test_kauth)
