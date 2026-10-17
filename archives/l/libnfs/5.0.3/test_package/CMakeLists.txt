cmake_minimum_required(VERSION 3.15)
project(test_libnfs C)

# Find the package via the Conan-generated CMakeDeps config.
# conanfile.py exposes cmake_file_name=libnfs, cmake_target_name=libnfs::nfs.
find_package(libnfs REQUIRED)

add_executable(test_libnfs test.c)
target_link_libraries(test_libnfs libnfs::nfs)

enable_testing()
add_test(NAME test_libnfs COMMAND test_libnfs)
