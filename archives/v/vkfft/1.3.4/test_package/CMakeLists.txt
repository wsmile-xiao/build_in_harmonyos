cmake_minimum_required(VERSION 3.15)
project(test_vkfft CXX)

set(CMAKE_CXX_STANDARD 17)

# Find the package via Conan-generated CMakeDeps
find_package(VkFFT REQUIRED)

add_executable(test_vkfft test_vkfft.cpp)
target_link_libraries(test_vkfft VkFFT::VkFFT)

enable_testing()
add_test(NAME test_vkfft COMMAND test_vkfft)
