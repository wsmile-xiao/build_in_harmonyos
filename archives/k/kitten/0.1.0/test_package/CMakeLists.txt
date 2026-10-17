cmake_minimum_required(VERSION 3.15)
project(test_kitten CXX)

# 消费者按上游口径要求 C++17（根 CMakeLists.txt 的 target_compile_features cxx_std_17）
find_package(kitten REQUIRED)

add_executable(test_kitten test_package.cpp)
# 上游 README 的消费口径：find_package(kitten) + rvarago::kitten
target_link_libraries(test_kitten rvarago::kitten)
target_compile_features(test_kitten PRIVATE cxx_std_17)
