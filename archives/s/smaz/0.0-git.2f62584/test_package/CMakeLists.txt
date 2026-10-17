cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(smaz CONFIG REQUIRED)

add_executable(test_smaz test_smaz.c)
target_link_libraries(test_smaz PRIVATE smaz::smaz)
target_compile_features(test_smaz PRIVATE c_std_99)
