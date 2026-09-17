cmake_minimum_required(VERSION 3.15)
project(test_sbsms CXX)

# sbsms::sbsms comes from the Conan-generated CMakeDeps config (the package also
# installs its own upstream sbsmsConfig.cmake; either resolves the same target).
find_package(sbsms REQUIRED)

add_executable(test_sbsms test_sbsms.cpp)
target_link_libraries(test_sbsms PRIVATE sbsms::sbsms)
target_compile_features(test_sbsms PRIVATE cxx_std_17)
