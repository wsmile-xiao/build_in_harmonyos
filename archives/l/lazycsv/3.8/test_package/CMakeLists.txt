cmake_minimum_required(VERSION 3.15)
project(test_lazycsv CXX)

# 通过 Conan 生成的 CMakeDeps 查找包（公开 cmake target: lazycsv::lazycsv）
find_package(lazycsv REQUIRED)

add_executable(test_lazycsv test.cpp)
target_link_libraries(test_lazycsv lazycsv::lazycsv)
target_compile_features(test_lazycsv PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_lazycsv COMMAND test_lazycsv)
