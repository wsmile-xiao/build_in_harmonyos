cmake_minimum_required(VERSION 3.15)
project(test_libydpdict C)

# Find the package via Conan-generated CMakeDeps
find_package(libydpdict REQUIRED)

add_executable(test_libydpdict test.c)
target_link_libraries(test_libydpdict libydpdict::libydpdict)

# rule12 鸿蒙特有端到端消费者用例：生成真实词典文件对 -> open -> 查询 -> close
add_executable(test_ydpdict_e2e test_ydpdict_e2e.c)
target_link_libraries(test_ydpdict_e2e libydpdict::libydpdict)

enable_testing()
add_test(NAME test_libydpdict COMMAND test_libydpdict)
add_test(NAME test_ydpdict_e2e COMMAND test_ydpdict_e2e)
