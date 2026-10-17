cmake_minimum_required(VERSION 3.15)
project(test_libnsl C)

find_package(libnsl REQUIRED)

add_executable(test_libnsl test_libnsl.c)
target_link_libraries(test_libnsl libnsl::libnsl)

# libnsl's public headers include <rpc/rpc.h>, which belongs to libtirpc.
# Normally libnsl::libnsl propagates those include roots; the published
# libtirpc/1.3.7 cpp_info currently exposes none, so the conanfile passes
# them explicitly (same workaround as libdap/3.20.6).
if(LIBNSL_EXTRA_INCLUDE_DIRS)
  target_include_directories(test_libnsl PRIVATE ${LIBNSL_EXTRA_INCLUDE_DIRS})
endif()

enable_testing()
add_test(NAME test_libnsl COMMAND test_libnsl)
