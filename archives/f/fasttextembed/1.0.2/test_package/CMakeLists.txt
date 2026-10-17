cmake_minimum_required(VERSION 3.15)
project(test_fasttextembed C)

# 消费者从 conan 包取词表路径（由 test_package/conanfile.py 传入）
if(NOT DEFINED VOCAB_PATH)
    set(VOCAB_PATH "vocab.tsv")
endif()

find_package(fasttextembed REQUIRED)

add_executable(test_fasttextembed test.c)
target_link_libraries(test_fasttextembed fasttextembed::fasttextembed)
target_compile_definitions(test_fasttextembed PRIVATE VOCAB_PATH="${VOCAB_PATH}")

enable_testing()
add_test(NAME test_fasttextembed COMMAND test_fasttextembed)