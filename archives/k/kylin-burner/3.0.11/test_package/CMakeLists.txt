cmake_minimum_required(VERSION 3.15)
project(test_kylin-burner C)

# Consumer example for the kylin-burner package.  The runtime test is
# driven by test_package/conanfile.py (compile of test.c against the
# installed headers + execution of the bin/burner launcher via test.sh);
# this CMake file documents the CMakeDeps consumer shape for the three
# installed libraries.
find_package(kylin-burner CONFIG REQUIRED)

add_executable(test_kylin-burner test.c)
target_link_libraries(test_kylin-burner PRIVATE kylin-burner::kylin-burner)

enable_testing()
add_test(NAME smoke COMMAND test_kylin-burner)
