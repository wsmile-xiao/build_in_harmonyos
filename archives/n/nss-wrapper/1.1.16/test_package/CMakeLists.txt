cmake_minimum_required(VERSION 3.15)
project(test_nss_wrapper C)

add_executable(test_nss_wrapper test_nss_wrapper.c)
target_compile_definitions(
    test_nss_wrapper
    PRIVATE
        NSS_WRAPPER_TEST_LIBRARY="${NSS_WRAPPER_TEST_LIBRARY}"
)

if(CMAKE_DL_LIBS)
    target_link_libraries(test_nss_wrapper PRIVATE ${CMAKE_DL_LIBS})
endif()
