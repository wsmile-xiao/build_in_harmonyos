cmake_minimum_required(VERSION 3.16)
project(test_package LANGUAGES CXX)

# libgpr ships no CMake config (module split, cmake_find_mode=none).
# Link the static archive directly; abseil comes through CMakeDeps
# (gpr public headers include absl/synchronization/*.h).
find_package(abseil-cpp REQUIRED)

add_executable(test_package test_package.cc)
target_include_directories(test_package PRIVATE ${LIBGPR_INC_DIR})
target_compile_features(test_package PRIVATE cxx_std_17)
target_link_libraries(test_package PRIVATE
  ${LIBGPR_LIB_DIR}/libgpr.a
  abseil-cpp::abseil-cpp
)

# Register unconditionally: the Conan CI profile is native, but a cross
# build sets BUILD_TESTING=OFF (tools.build:skip_test) and an empty ctest
# would then fail with --no-tests=error.
enable_testing()
add_test(NAME test_package COMMAND test_package)