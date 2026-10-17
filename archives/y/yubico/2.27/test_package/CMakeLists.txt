cmake_minimum_required(VERSION 3.15)
project(test_package C)

add_executable(test_yubico test.c)
target_compile_definitions(test_yubico PRIVATE
    PAM_MODULE_PATH="${PAM_MODULE_DIR}/pam_yubico.so")
target_link_libraries(test_yubico PRIVATE ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_yubico COMMAND test_yubico)
