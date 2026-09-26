cmake_minimum_required(VERSION 3.15)
project(test_pipewire C)

# Find the package via Conan-generated CMakeDeps
find_package(pipewire REQUIRED)

add_executable(test_pipewire test.c)
target_link_libraries(test_pipewire pipewire::pipewire)

add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos pipewire::pipewire)

enable_testing()
add_test(NAME test_pipewire COMMAND test_pipewire)
add_test(NAME test_ohos COMMAND test_ohos)
