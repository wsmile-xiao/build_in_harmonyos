cmake_minimum_required(VERSION 3.15)
project(test_libvpl C)

# Conan-generated VPLConfig.cmake (CMakeDeps); the package exports the
# upstream target name VPL::dispatcher.
find_package(VPL REQUIRED)

# Consumer test: exercises the public oneVPL 2.x loader API end to end.
add_executable(test_libvpl test_libvpl.c)
target_link_libraries(test_libvpl PRIVATE VPL::dispatcher)

# OHOS-specific consumer test: platform facts that only hold on the packaged
# HarmonyOS build (legacy dispatcher compiled, no Intel runtime present).
add_executable(test_libvpl_ohos test_libvpl_ohos.c)
target_link_libraries(test_libvpl_ohos PRIVATE VPL::dispatcher)
# The legacy 1.x entry points are marked MFX_DEPRECATED; calling them is the
# point of this test, so silence the deprecation diagnostics for it only.
if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
  target_compile_options(test_libvpl_ohos PRIVATE -Wno-deprecated-declarations)
endif()

enable_testing()
add_test(NAME test_libvpl COMMAND test_libvpl)
add_test(NAME test_libvpl_ohos COMMAND test_libvpl_ohos)
