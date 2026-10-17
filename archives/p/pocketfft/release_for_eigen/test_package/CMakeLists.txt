cmake_minimum_required(VERSION 3.15)
project(test_pocketfft CXX)

# Find the package via Conan-generated CMakeDeps
find_package(pocketfft REQUIRED)

add_executable(test_pocketfft test_pocketfft.cc)
target_link_libraries(test_pocketfft pocketfft::pocketfft)

enable_testing()
add_test(NAME test_pocketfft COMMAND test_pocketfft)
