cmake_minimum_required(VERSION 3.15)
# Dawn/webgpu_dawn is a C++ library; enable CXX so the linker pulls in
# libc++ (std::string, exceptions) when linking the consumer test.
project(test_dawn C CXX)

# Find the package via Conan-generated CMakeDeps
find_package(dawn REQUIRED)
# webgpu_dawn bundles Dawn objects only; the consumer links the ohpcd
# abseil static libraries for the symbols Dawn references.
find_package(absl CONFIG REQUIRED)

file(GLOB ABSL_STATIC_LIBS "${ABSEIL_LIB_DIR}/libabsl_*.a")
if(NOT ABSL_STATIC_LIBS)
  message(FATAL_ERROR "test_dawn: no libabsl_*.a found under ${ABSEIL_LIB_DIR}")
endif()

add_executable(test_dawn test.cpp)
target_link_libraries(test_dawn dawn::dawn ${ABSL_STATIC_LIBS})

enable_testing()
add_test(NAME test_dawn COMMAND test_dawn)