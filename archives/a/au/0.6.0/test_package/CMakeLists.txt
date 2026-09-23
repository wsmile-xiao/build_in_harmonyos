cmake_minimum_required(VERSION 3.15)
project(test_au CXX)

find_package(Au REQUIRED CONFIG)

add_executable(test_au test_au_ohos.cpp)
target_link_libraries(test_au PRIVATE Au::au)
target_compile_features(test_au PRIVATE cxx_std_17)

enable_testing()
add_test(NAME au_ohos_consumer COMMAND test_au)