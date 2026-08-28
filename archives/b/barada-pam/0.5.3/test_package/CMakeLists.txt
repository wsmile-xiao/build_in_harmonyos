cmake_minimum_required(VERSION 3.15)
project(test_barada_pam LANGUAGES CXX)

add_executable(test_barada_pam test.cpp)
target_include_directories(test_barada_pam PRIVATE "${BARADA_PAM_INCLUDE_DIR}")
target_link_libraries(test_barada_pam PRIVATE ${CMAKE_DL_LIBS})
