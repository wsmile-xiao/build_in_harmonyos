cmake_minimum_required(VERSION 3.15)
project(pastix_test_package C)

find_package(pastix REQUIRED)

add_executable(test_pastix_solve test_pastix_solve.c)
target_link_libraries(test_pastix_solve PRIVATE PASTIX::pastix)

add_executable(test_pastix_contract test_pastix_contract.c)
target_link_libraries(test_pastix_contract PRIVATE PASTIX::pastix)

enable_testing()
add_test(NAME pastix_solve COMMAND test_pastix_solve)
add_test(NAME pastix_contract COMMAND test_pastix_contract)
