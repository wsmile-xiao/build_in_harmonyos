cmake_minimum_required(VERSION 3.15)
project(test_linenoise-ng C)

# Find the package via Conan-generated CMakeDeps
find_package(linenoise-ng REQUIRED)

add_executable(test_linenoise-ng test.c)
target_link_libraries(test_linenoise-ng linenoise-ng::linenoise-ng)

# OHOS headless regression suite (15 assertions, incl. shrink->Save NULL-deref
# regression covered by patch 0002) — delivered with the PR so the documented
# verification command is reproducible from the repo.
add_executable(ohos_test ohos_test.c)
target_link_libraries(ohos_test linenoise-ng::linenoise-ng)

enable_testing()
add_test(NAME test_linenoise-ng COMMAND test_linenoise-ng)
add_test(NAME ohos_test COMMAND ohos_test)
