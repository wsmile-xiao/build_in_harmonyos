cmake_minimum_required(VERSION 3.15)
project(sysrepo_test_package C)

find_package(sysrepo REQUIRED)

add_executable(test_sysrepo test_sysrepo.c)
target_link_libraries(test_sysrepo PRIVATE sysrepo::sysrepo)

enable_testing()
add_test(NAME test_sysrepo COMMAND test_sysrepo)
# sysrepo keeps its datastore on disk plus shared-memory control files; point
# both at the writable test build dir instead of the compiled-in install
# prefix, which is not guaranteed writable for a consumed package.
set_property(TEST test_sysrepo PROPERTY ENVIRONMENT
    "SYSREPO_REPOSITORY_PATH=${CMAKE_CURRENT_BINARY_DIR}/test_repo"
    "SYSREPO_SHM_PREFIX=_conan_sr_test")
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/test_repo/datastore")
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/test_repo/modules")
