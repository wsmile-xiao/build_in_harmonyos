cmake_minimum_required(VERSION 3.20)
project(test_linux_pam C)

find_package(linux-pam REQUIRED)

add_executable(test_linux_pam test_linux_pam.c)
target_link_libraries(test_linux_pam PRIVATE linux-pam::pam linux-pam::pam_misc)
target_compile_definitions(test_linux_pam PRIVATE
    LINUX_PAM_TEST_MODULE="${LINUX_PAM_TEST_MODULE}"
)
