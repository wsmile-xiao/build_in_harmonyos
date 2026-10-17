cmake_minimum_required(VERSION 3.15)
project(test_kdbindings CXX)

# Find the package via Conan-generated CMakeDeps
find_package(KDBindings REQUIRED)

add_executable(test_kdbindings test_kdbindings.cpp)
target_link_libraries(test_kdbindings KDAB::KDBindings)
target_compile_features(test_kdbindings PRIVATE cxx_std_17)

# 鸿蒙特有测试（rule12）：独立入口，验证 uname 平台值绑定链、HMDFS I/O
# round-trip、Signal 回调顺序/断开语义与 /tmp EROFS 只读特性
add_executable(test_harmony_specific test_harmony_specific.cpp)
target_link_libraries(test_harmony_specific KDAB::KDBindings)
target_compile_features(test_harmony_specific PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_kdbindings COMMAND test_kdbindings)
add_test(NAME test_harmony_specific COMMAND test_harmony_specific)
