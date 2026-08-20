cmake_minimum_required(VERSION 3.20)
project(test_pam_wrapper C)

find_package(pam_wrapper REQUIRED)
find_package(linux-pam REQUIRED)

add_executable(test_pam_wrapper test_pam_wrapper.c)
target_link_libraries(test_pam_wrapper PRIVATE pam_wrapper::pam_wrapper linux-pam::pam ${CMAKE_DL_LIBS})
target_include_directories(test_pam_wrapper PRIVATE "${LINUX_PAM_INCLUDE_DIR}")
target_compile_definitions(test_pam_wrapper PRIVATE
    PAM_WRAPPER_TEST_LIBRARY="${PAM_WRAPPER_TEST_LIBRARY}"
)
