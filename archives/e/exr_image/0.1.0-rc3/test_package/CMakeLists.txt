cmake_minimum_required(VERSION 3.15)
project(test_exr_image C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(exr_image REQUIRED CONFIG)

add_executable(test_exr_image test.c)
target_link_libraries(test_exr_image exr_image::exr_image)

# HarmonyOS 专项测试：内存版公开 ABI（multipart/负向/tiled/deep），
# 不依赖 /tmp 可写（OHOS 设备 /tmp 为只读 erofs），与消费者测试分别计数。
add_executable(test_ohos_specific test_ohos_specific.c)
target_link_libraries(test_ohos_specific exr_image::exr_image)

enable_testing()
add_test(NAME test_exr_image COMMAND test_exr_image)
add_test(NAME test_ohos_specific COMMAND test_ohos_specific)
