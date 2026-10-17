cmake_minimum_required(VERSION 3.15)
project(test_libhwy_test CXX)

# 消费者视角：只用包内 CMake 配置暴露的 hwy::hwy_test（CMakeDeps 生成）
find_package(hwy REQUIRED)

add_executable(test_libhwy_test test_libhwy_test.cpp)
target_link_libraries(test_libhwy_test PRIVATE hwy::hwy_test)
target_compile_features(test_libhwy_test PRIVATE cxx_std_17)
# 交付的 hwy/tests/hwy_gtest.h 在 standalone 形态下需要该宏（libhwy-test.pc 同样注入）
target_compile_definitions(test_libhwy_test PRIVATE HWY_TEST_STANDALONE=1)

enable_testing()
add_test(NAME test_libhwy_test COMMAND test_libhwy_test)
