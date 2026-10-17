cmake_minimum_required(VERSION 3.15)
project(test_libgta C)

# Find the package via Conan-generated CMakeDeps
find_package(libgta REQUIRED)

add_executable(test_libgta test.c)
target_link_libraries(test_libgta libgta::libgta)

# The test binary is executed from test_package/conanfile.py via
# self.run(..., env="conanrun") — no ctest indirection.
