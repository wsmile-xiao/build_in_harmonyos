cmake_minimum_required(VERSION 3.15)
project(liquid_ohos_consumer C)

find_package(liquid REQUIRED)

add_executable(liquid_ohos_consumer liquid-ohos-test.c)
target_link_libraries(liquid_ohos_consumer liquid::liquid)
