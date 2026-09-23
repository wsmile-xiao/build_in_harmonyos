cmake_minimum_required(VERSION 3.8)
project(glm_test CXX)

find_package(glm CONFIG REQUIRED)

add_executable(test_glm test_package.cpp)
target_link_libraries(test_glm PRIVATE glm::glm)
target_compile_features(test_glm PRIVATE cxx_std_11)
