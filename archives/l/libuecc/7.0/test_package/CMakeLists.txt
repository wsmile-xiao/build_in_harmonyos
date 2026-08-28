# libuecc test_package — CMake script for the Conan consumer test
#
# IMPORTANT: Upstream CMakeLists.txt declares cmake_minimum_required(VERSION 2.6);
# CMake 4.x refuses such old policy, so we enforce CMP<3.5 deprecation cap
# BEFORE the project() call (project() may otherwise emit a hard error).
cmake_minimum_required(VERSION 3.15)
set(CMAKE_POLICY_VERSION_MINIMUM 3.5 CACHE STRING "" FORCE)

project(test_libuecc C)

# Find the package via Conan-generated CMakeDeps (component name follows
# what the recipe sets in cpp_info.libs / name).
find_package(libuecc REQUIRED)

add_executable(test_libuecc test_libuecc.c)
# CMakeDeps generates the imported target name from the package `name`
# attribute, so the link target is `libuecc::libuecc` (not `libuecc::uecc`,
# which is only the archive filename produced by upstream).
target_link_libraries(test_libuecc libuecc::libuecc)

enable_testing()
add_test(NAME test_libuecc COMMAND test_libuecc)