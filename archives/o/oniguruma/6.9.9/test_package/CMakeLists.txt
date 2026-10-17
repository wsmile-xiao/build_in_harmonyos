cmake_minimum_required(VERSION 3.15)
project(test_oniguruma C)

# Find the package via Conan-generated CMakeDeps
find_package(oniguruma REQUIRED)

add_executable(test_oniguruma test.c)
target_link_libraries(test_oniguruma oniguruma::onig)

add_executable(test_oniguruma_ohos test_oniguruma_ohos.c)
target_link_libraries(test_oniguruma_ohos oniguruma::onig)

enable_testing()
add_test(NAME test_oniguruma COMMAND test_oniguruma)
add_test(NAME test_oniguruma_ohos COMMAND test_oniguruma_ohos)
