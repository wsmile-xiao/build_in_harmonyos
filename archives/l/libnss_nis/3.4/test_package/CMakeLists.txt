cmake_minimum_required(VERSION 3.15)
project(test_libnss_nis C)

# Find the package via Conan-generated CMakeDeps
find_package(libnss_nis REQUIRED)

# The consumer links the installed module artifact (validates that the
# conan package exposes a usable link target) and dlopen()s the shared
# module at runtime to exercise the public _nss_nis_* entry points.
add_executable(test_libnss_nis test.c)
target_link_libraries(test_libnss_nis libnss_nis::libnss_nis ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_libnss_nis COMMAND test_libnss_nis)
