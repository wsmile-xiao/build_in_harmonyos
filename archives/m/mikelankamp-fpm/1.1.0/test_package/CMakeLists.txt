cmake_minimum_required(VERSION 3.15)
project(mikelankamp_fpm_test_package CXX)

# The upstream library requires C++11 or higher; CMAKE_CXX_STANDARD is left to
# the conan toolchain (the OHOS profile pins cppstd=17), so this consumer also
# proves the delivered headers compile as C++17.
find_package(fpm REQUIRED CONFIG)

add_executable(consumer consumer.cpp)
target_link_libraries(consumer PRIVATE fpm::fpm)
