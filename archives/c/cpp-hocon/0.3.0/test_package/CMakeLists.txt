cmake_minimum_required(VERSION 3.13)
project(test_cpp_hocon CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(cpp-hocon CONFIG REQUIRED)
# Direct lookup of the boost pair (also a cpp-hocon requirement); see the
# note in conanfile.py about the custom-layout boost1.84 package.
find_package(Boost 1.84.0 CONFIG REQUIRED COMPONENTS headers filesystem program_options)
find_package(hocon-boost-thread 1.84.0 CONFIG REQUIRED)

# Parse HOCON text, resolve substitutions and read typed values back:
# exercises the public API surface (config_value_factory / config /
# config_object / config_value), the leatherman compat shim (the
# public headers pull leatherman/locale/locale.hpp) and the link
# against libhocon + boost static libs.
add_executable(test_cpp_hocon test_package.cpp)
target_link_libraries(test_cpp_hocon PRIVATE cpp-hocon::cpp-hocon Boost::headers Boost::filesystem Boost::program_options boost1.84-thread::boost1.84-thread)
# Statically link the C++ runtime into the probe binary: on OHOS the
# dynamic libc++_shared.so lives in the SDK sysroot, not in the loader's
# default search path, so an unqualified test executable cannot start
# (same approach as archives/a/argp-standalone's test probe).
target_link_options(test_cpp_hocon PRIVATE -static-libstdc++)

enable_testing()
add_test(NAME test_cpp_hocon COMMAND test_cpp_hocon)
