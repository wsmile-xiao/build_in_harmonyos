cmake_minimum_required(VERSION 3.15)
project(test_pathie_cpp CXX)

# 经 Conan CMakeDeps 消费被测包（conanfile.py package_info: cmake_file_name=Pathie）
find_package(Pathie REQUIRED)

add_executable(test_pathie_cpp consumer.cpp)
target_link_libraries(test_pathie_cpp Pathie::Pathie)
# 上游头文件按 C++98 编写，但 testhelpers/stream 组件与本消费者用到的
# std::string 接口在 C++11 下同样可用（profile cppstd=17）。
target_compile_features(test_pathie_cpp PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_pathie_cpp COMMAND test_pathie_cpp)
