cmake_minimum_required(VERSION 3.15)
# Compilers, CMAKE_SYSTEM_PROCESSOR and the system name are provided by the
# Conan-generated CMakeToolchain (see test_package/conanfile.py generate()).
# Do not override CMAKE_SYSTEM_NAME here: the OHOS profile must not be
# disguised as Linux. project() is called after the toolchain is loaded.
project(test_mdds CXX)

# C++20 is required by mdds 3.x public headers.
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(mdds REQUIRED CONFIG)
# Boost is not found/linked directly here: it is a transitive requirement
# of mdds, propagated by the main recipe via cpp_info.requires=["boost::boost"],
# so the mdds::mdds target already brings Boost::boost and its include dirs.

add_executable(test_mdds test_mdds.cpp)
target_link_libraries(test_mdds PRIVATE mdds::mdds)

enable_testing()
add_test(NAME test_mdds COMMAND test_mdds)
