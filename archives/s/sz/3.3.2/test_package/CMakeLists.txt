cmake_minimum_required(VERSION 3.15)
project(test_sz CXX)

# 经 CMakeDeps 发现 SZ3（cmake_file_name=SZ3，target=SZ3::SZ3，传递链接 zstd）
find_package(SZ3 REQUIRED)

add_executable(test_sz test_sz.cpp)
target_compile_features(test_sz PRIVATE cxx_std_17)
target_link_libraries(test_sz SZ3::SZ3)

enable_testing()
add_test(NAME test_sz COMMAND test_sz)
