cmake_minimum_required(VERSION 3.15)
project(ocsd_test LANGUAGES C)

find_package(libopencsd CONFIG REQUIRED)

add_executable(ocsd_consumer test_consumer.c)
target_link_libraries(ocsd_consumer PRIVATE libopencsd::libopencsd)

# dlopen 专项测试：不链接库，仅按路径 dlopen 打包出的 libopencsd.so
add_executable(ocsd_dlopen test_dlopen.c)
target_link_libraries(ocsd_dlopen PRIVATE ${CMAKE_DL_LIBS})
