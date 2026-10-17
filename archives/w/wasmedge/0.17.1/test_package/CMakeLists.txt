cmake_minimum_required(VERSION 3.15)
project(test_wasmedge C CXX)

find_package(wasmedge REQUIRED)

add_executable(test_wasmedge test_wasmedge.c)
set_target_properties(test_wasmedge PROPERTIES LINKER_LANGUAGE CXX)
target_link_libraries(test_wasmedge wasmedge::wasmedge)

enable_testing()
add_test(NAME wasmedge_version_api COMMAND test_wasmedge --version-api)
add_test(NAME wasmedge_vm_lifecycle COMMAND test_wasmedge --vm-lifecycle)
add_test(NAME wasmedge_vm_execute_add COMMAND test_wasmedge --vm-execute-add)
add_test(NAME wasmedge_vm_repeat_execute COMMAND test_wasmedge --vm-repeat-execute)
add_test(NAME wasmedge_reject_invalid_module COMMAND test_wasmedge --reject-invalid-module)
add_test(NAME wasmedge_reject_missing_function COMMAND test_wasmedge --reject-missing-function)
