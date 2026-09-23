cmake_minimum_required(VERSION 3.15)
project(test_mifluz CXX)

# Find the package via Conan-generated CMakeDeps
find_package(mifluz REQUIRED)

add_executable(test_mifluz test.cpp)
target_compile_features(test_mifluz PRIVATE cxx_std_11)
# The installed clib.h carries fallback declarations for libc functions that
# the build-time config.h suppresses via HAVE_* macros; mirror them here.
target_compile_definitions(test_mifluz PRIVATE
  NOSTREAM
  HAVE_GETCWD HAVE_MEMCMP HAVE_MEMCPY HAVE_MEMMOVE HAVE_RAISE
  HAVE_SNPRINTF HAVE_STRERROR HAVE_VSNPRINTF HAVE_STRNCOLL
  HAVE_STRCASESTR HAVE_STRCASECMP HAVE_STRNCASECMP)
target_link_libraries(test_mifluz mifluz::mifluz)

enable_testing()
add_test(NAME test_mifluz COMMAND test_mifluz)
