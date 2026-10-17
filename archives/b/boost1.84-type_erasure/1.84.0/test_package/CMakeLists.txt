cmake_minimum_required(VERSION 3.16)
project(boost184_type_erasure_test_package CXX)

find_package(boost1.84-type_erasure REQUIRED CONFIG)
find_package(Threads REQUIRED)

add_executable(test_boost_type_erasure test_boost_type_erasure.cpp)
target_link_libraries(test_boost_type_erasure PRIVATE boost1.84-type_erasure::type_erasure Threads::Threads)

# OHOS: statically link the libc++ runtime (-static-libstdc++) so the test
# binary runs without LD_LIBRARY_PATH pointing at the SDK's
# libc++_shared.so (conanrun env does not contain the profile buildenv SDK
# library path; dynamic linking fails with
# "Error loading shared library libc++_shared.so", rc=127).
target_link_options(test_boost_type_erasure PRIVATE -static-libstdc++)

enable_testing()
add_test(NAME boost184_type_erasure_smoke COMMAND test_boost_type_erasure)
