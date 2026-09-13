cmake_minimum_required(VERSION 3.15)
project(test_lzham C CXX)

find_package(lzham REQUIRED CONFIG)

add_executable(test_lzham test_lzham.c)
# The public API is C, but the packaged implementation is a C++ static
# library; use the C++ linker so its standard library is linked as well.
set_property(TARGET test_lzham PROPERTY LINKER_LANGUAGE CXX)
target_link_libraries(test_lzham PRIVATE lzham::lzham)

# The package recipe intentionally uses CMAKE_SYSTEM_NAME=Linux for the
# portable CMake platform module.  The explicit Conan flag keeps the OHOS
# consumer test enabled without relying on that implementation detail.
if(LZHAM_OHOS_TEST OR CMAKE_SYSTEM_NAME STREQUAL "OHOS" OR
   CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR
   CMAKE_C_COMPILER_TARGET MATCHES "ohos")
    add_executable(test_lzham_ohos test_ohos.c)
    set_property(TARGET test_lzham_ohos PROPERTY LINKER_LANGUAGE CXX)
    target_link_libraries(test_lzham_ohos PRIVATE lzham::lzham)
endif()
