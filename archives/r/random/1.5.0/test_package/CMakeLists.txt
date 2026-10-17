cmake_minimum_required(VERSION 3.15)
project(test_random CXX)

# Find the package via Conan-generated CMakeDeps
find_package(random REQUIRED)
find_package(Threads REQUIRED)

add_executable(test_random test.cpp)
target_link_libraries(test_random random::random)

# HarmonyOS 专项测试：多线程 thread_local 隔离 + OHOS 熵源 + 范围/类型推导
add_executable(test_random_hmos test_random_hmos.cpp)
target_link_libraries(test_random_hmos random::random Threads::Threads)

foreach(tgt test_random test_random_hmos)
    set_target_properties(${tgt} PROPERTIES
        CXX_STANDARD 17
        CXX_STANDARD_REQUIRED ON
    )
endforeach()

enable_testing()
add_test(NAME test_random COMMAND test_random)
add_test(NAME test_random_hmos COMMAND test_random_hmos)