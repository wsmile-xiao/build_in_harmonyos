cmake_minimum_required(VERSION 3.15)
project(test_libfbclient CXX)

enable_testing()

# Conan-generated CMakeDeps config for the package under test.
find_package(libfbclient REQUIRED)

add_executable(test_libfbclient test_libfbclient.cpp)
target_compile_features(test_libfbclient PRIVATE cxx_std_17)
target_link_libraries(test_libfbclient PRIVATE libfbclient::libfbclient)

# dladdr/dlopen are used by the HarmonyOS artifact check.
find_library(DL_LIBRARY dl)
if (DL_LIBRARY)
    target_link_libraries(test_libfbclient PRIVATE ${DL_LIBRARY})
endif ()

add_test(NAME test_libfbclient COMMAND test_libfbclient)
